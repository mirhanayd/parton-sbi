import os
import sys
import json
import argparse
import subprocess
import concurrent.futures
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hepdata.download import download_dataset
from hepdata.parse import parse_dataset
from hepdata.schemas import validate_metadata
from validation.binning import apply_cuts
from validation.covariance import build_covariance_matrix
from validation.chi_square import calculate_chi2_covariance
from validation.cache import TheoryCache
from validation.uncertainty import calculate_pdf_uncertainty, calculate_scale_uncertainty

def get_apfel_cli_path():
    backend_path = os.environ.get("APFEL_BACKEND_BIN")
    if backend_path and os.path.exists(backend_path):
        return backend_path
        
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    default_path = os.path.join(project_root, "physics-engine/build/apfel_cli")
    if os.path.exists(default_path):
        return default_path
        
    return "apfel_cli"

def call_apfel(x, q2, pdf_set, pdf_member, order, apfel_bin, pdf_members=None, scale_members=None):
    request = {
        "schema_version": 1,
        "process": "nc_dis",
        "projectile": "electron",
        "target": "proton",
        "x": float(x),
        "q2": float(q2),
        "order": str(order),
        "pdf_set": str(pdf_set),
        "pdf_member": int(pdf_member),
        "mu_f_over_q": 1.0,
        "mu_r_over_q": 1.0
    }
    
    if pdf_members:
        request["pdf_members"] = [int(m) for m in pdf_members]
    if scale_members:
        request["scale_members"] = [[float(s[0]), float(s[1])] for s in scale_members]
        
    proc = subprocess.Popen(
        [apfel_bin],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=json.dumps(request))
    
    if proc.returncode != 0:
        raise RuntimeError(f"apfel_cli returned exit code {proc.returncode}. Stderr: {stderr.strip()}")
        
    res = json.loads(stdout)
    if not res.get("success"):
        err = res.get("error", {})
        raise RuntimeError(f"APFEL++ error [code={err.get('code')}]: {err.get('message')} - {err.get('hint')}")
        
    return res

def evaluate_point(args):
    idx, row, pdf_set, pdf_member, order, apfel_bin, pdf_members, scale_members, cache_inst = args
    
    # Check cache
    # Extract cache parameters
    backend = "apfel"
    backend_version = "4.8.0" # Checked in apfelxx.h / version
    scales = "mu_R = mu_F = Q"
    process = "nc_dis"
    
    cached = cache_inst.get(
        backend, backend_version, pdf_set, pdf_member, order, 
        row["x"], row["Q2"], scales, process, pdf_members, scale_members
    )
    if cached is not None:
        return idx, cached
        
    # Evaluate using subprocess
    res = call_apfel(
        row["x"], row["Q2"], pdf_set, pdf_member, order, apfel_bin, 
        pdf_members, scale_members
    )
    
    # Save cache
    cache_inst.set(
        backend, backend_version, pdf_set, pdf_member, order, 
        row["x"], row["Q2"], scales, process, res, pdf_members, scale_members
    )
    
    return idx, res

def run_uncertainty_pipeline(dataset_id, backend, order, pdf_set, pdf_member, q2_min, output_dir, do_pdf_unc, do_scale_var):
    print("=" * 60)
    print("HERA Systematic Theory Uncertainties Pipeline")
    print("=" * 60)
    print(f"Dataset:      {dataset_id}")
    print(f"Backend:      {backend}")
    print(f"Order:        {order}")
    print(f"PDF Set:      {pdf_set}")
    print(f"Q2 Min Cut:   {q2_min} GeV^2")
    print(f"PDF Unc:      {do_pdf_unc}")
    print(f"Scale Var:    {do_scale_var}")
    print(f"Output Dir:   {output_dir}")
    print("-" * 60)
    
    # 1. Download and Parse Dataset
    data_file = download_dataset()
    df_raw = parse_dataset(data_file)
    df = apply_cuts(df_raw, q2_min=q2_min).copy()
    n_points = len(df)
    print(f"Loaded HERA data. Bins inside kinematic cuts: {n_points}")
    if n_points == 0:
        raise ValueError("No data points remaining after cuts.")
        
    # 2. Probe PDF Set Metadata (Size & ErrorType) using first point
    apfel_bin = get_apfel_cli_path()
    first_row = df.iloc[0]
    print(f"Probing LHAPDF metadata for '{pdf_set}'...")
    probe_res = call_apfel(first_row["x"], first_row["Q2"], pdf_set, pdf_member, order, apfel_bin)
    meta = probe_res.get("metadata", {})
    pdf_error_type = meta.get("pdf_error_type", "hessian")
    pdf_size = meta.get("pdf_size", 1)
    
    print(f"PDF Set Size: {pdf_size} members. ErrorType: {pdf_error_type}")
    
    # Determine members list if uncertainty is enabled
    pdf_members = []
    if do_pdf_unc and pdf_size > 1:
        pdf_members = list(range(1, pdf_size))
        
    # 7-point scale variations (excluding central scale)
    scale_members = []
    if do_scale_var:
        scale_members = [
            [0.5, 0.5],
            [0.5, 1.0],
            [1.0, 0.5],
            [1.0, 2.0],
            [2.0, 1.0],
            [2.0, 2.0]
        ]
        
    # Initialize Cache
    cache_inst = TheoryCache()
    
    # 3. Parallel Evaluation
    print("Evaluating central values, PDF variations, and scale variations...")
    eval_args = []
    for idx, row in df.iterrows():
        eval_args.append((
            idx, row, pdf_set, pdf_member, order, apfel_bin, 
            pdf_members, scale_members, cache_inst
        ))
        
    results_map = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(evaluate_point, eval_args))
        
    for idx, res in results:
        results_map[idx] = res
        
    # Save cache
    cache_inst.save()
    
    # 4. Perform Uncertainty Computations
    theory_central = []
    pdf_unc_plus = []
    pdf_unc_minus = []
    scale_unc_plus = []
    scale_unc_minus = []
    mc_stat_unc = []
    
    for idx, row in df.iterrows():
        res = results_map[idx]
        f2_central = float(res["f2"])
        fl_central = float(res["fl"])
        
        # Calculate theoretical central reduced cross section
        y_plus = 1.0 + (1.0 - row["y"])**2
        central_reduced = f2_central - (row["y"]**2 / y_plus) * fl_central
        theory_central.append(central_reduced)
        
        # PDF uncertainty calculations
        if do_pdf_unc and "f2_pdf_members" in res:
            f2_m = np.array(res["f2_pdf_members"])
            fl_m = np.array(res["fl_pdf_members"])
            reduced_m = f2_m - (row["y"]**2 / y_plus) * fl_m
            
            p_plus, p_minus = calculate_pdf_uncertainty(central_reduced, reduced_m, pdf_error_type)
            pdf_unc_plus.append(p_plus)
            pdf_unc_minus.append(p_minus)
        else:
            pdf_unc_plus.append(0.0)
            pdf_unc_minus.append(0.0)
            
        # Scale uncertainty calculations
        if do_scale_var and "f2_scale_members" in res:
            f2_s = np.array(res["f2_scale_members"])
            fl_s = np.array(res["fl_scale_members"])
            reduced_s = f2_s - (row["y"]**2 / y_plus) * fl_s
            
            # Combine central value + variations list for envelope
            all_s_variations = [central_reduced] + list(reduced_s)
            s_plus, s_minus = calculate_scale_uncertainty(central_reduced, all_s_variations)
            scale_unc_plus.append(s_plus)
            scale_unc_minus.append(s_minus)
        else:
            scale_unc_plus.append(0.0)
            scale_unc_minus.append(0.0)
            
        # MC statistical uncertainty is zero for analytic APFEL++ predictions
        mc_stat_unc.append(0.0)
        
    # Assign arrays to DataFrame
    df["theory_central"] = theory_central
    df["pdf_uncertainty_plus"] = pdf_unc_plus
    df["pdf_uncertainty_minus"] = pdf_unc_minus
    df["scale_uncertainty_plus"] = scale_unc_plus
    df["scale_uncertainty_minus"] = scale_unc_minus
    df["mc_statistical_uncertainty"] = mc_stat_unc
    
    # 5. Covariance matrix and central Chi2
    cov = build_covariance_matrix(df)
    chi2_cov, pulls_cov = calculate_chi2_covariance(df["Sigma"].values, df["theory_central"].values, cov)
    ndf = n_points
    
    # Write summary files
    os.makedirs(output_dir, exist_ok=True)
    
    metadata = {
        "dataset_id": dataset_id,
        "name": "HERA Combined DIS NC e+p 920 GeV with Uncertainties",
        "description": "HERA combined reduced cross sections NC e+p scattering at E_p = 920 GeV with systematic theory uncertainties.",
        "source_url": "https://www.desy.de/h1zeus/herapdf20/",
        "download_date": "2026-07-16",
        "checksum_sha256": "dfa2fba16fa490600d10b7125189676343f07b40787d41a74a2d29d30fd8a8bc",
        "citation": "H1 and ZEUS Collaboration, H. Abramowicz et al., Eur. Phys. J. C 75 (2015) 580 [arXiv:1506.06042]."
    }
    validate_metadata(metadata)
    
    theory_config = {
        "backend": backend,
        "perturbative_order": order,
        "pdf_set": pdf_set,
        "pdf_member": pdf_member,
        "scales": "mu_F = mu_R = Q",
        "electroweak_assumptions": "LO electromagnetic, photon-exchange only (xF3 = 0, F_L = 0 in cross-section prefactor)",
        "heavy_flavor_settings": "Zero-Mass Variable Flavor Number Scheme (ZM-VFNS)",
        "beam_energies": {
            "electron_gev": 27.5,
            "proton_gev": 920.0
        }
    }
    
    summary = {
        "number_of_points": n_points,
        "chi_square": float(chi2_cov),
        "degrees_of_freedom": ndf,
        "chi_square_per_ndf": float(chi2_cov / ndf),
        "mean_ratio": float((df["Sigma"] / df["theory_central"]).mean()),
        "maximum_absolute_pull": float(np.max(np.abs(pulls_cov))),
        "data_source": "HERA1+2_NCep_920.dat",
        "theory_configuration": theory_config
    }
    
    # Save JSON files
    with open(os.path.join(output_dir, "dataset_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    with open(os.path.join(output_dir, "theory_config.json"), "w") as f:
        json.dump(theory_config, f, indent=2)
    with open(os.path.join(output_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
        
    df.to_csv(os.path.join(output_dir, "comparison.csv"), index=False)
    
    # comparison.json
    records = df.to_dict(orient="records")
    with open(os.path.join(output_dir, "comparison.json"), "w") as f:
        json.dump(records, f, indent=2)
        
    # 6. Plotting
    generate_uncertainty_plots(df, output_dir, do_pdf_unc, do_scale_var)
    print("Uncertainty analysis successfully completed.")
    print("=" * 60)

def generate_uncertainty_plots(df, output_dir, do_pdf_unc, do_scale_var):
    plt.rcParams.update({'font.size': 11})
    unique_q2 = sorted(df["Q2"].unique())
    target_q2s = [unique_q2[i] for i in np.linspace(0, len(unique_q2)-1, 6, dtype=int)]
    
    # Plot PDF Uncertainty Band (if enabled)
    if do_pdf_unc:
        plt.figure(figsize=(10, 6))
        colors = plt.cm.plasma(np.linspace(0, 0.8, len(target_q2s)))
        for q2_val, col in zip(target_q2s, colors):
            sub_df = df[df["Q2"] == q2_val].sort_values("x")
            if sub_df.empty:
                continue
            plt.plot(sub_df["x"], sub_df["theory_central"], '-', color=col, label=f"$Q^2 = {q2_val:.1f}$ GeV$^2$")
            plt.fill_between(
                sub_df["x"], 
                sub_df["theory_central"] - sub_df["pdf_uncertainty_minus"],
                sub_df["theory_central"] + sub_df["pdf_uncertainty_plus"],
                color=col, alpha=0.2
            )
        plt.xscale("log")
        plt.xlabel("Bjorken $x$")
        plt.ylabel("Reduced Cross Section $\sigma_{r, NC}^+$")
        plt.title("Theory Central Value and PDF Uncertainty Band")
        plt.legend(loc='best', ncol=2, fontsize=9)
        plt.grid(True, which="both", ls=":")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "pdf_uncertainty.svg"))
        plt.close()
        
    # Plot Scale Uncertainty Band (if enabled)
    if do_scale_var:
        plt.figure(figsize=(10, 6))
        colors = plt.cm.plasma(np.linspace(0, 0.8, len(target_q2s)))
        for q2_val, col in zip(target_q2s, colors):
            sub_df = df[df["Q2"] == q2_val].sort_values("x")
            if sub_df.empty:
                continue
            plt.plot(sub_df["x"], sub_df["theory_central"], '-', color=col, label=f"$Q^2 = {q2_val:.1f}$ GeV$^2$")
            plt.fill_between(
                sub_df["x"], 
                sub_df["theory_central"] - sub_df["scale_uncertainty_minus"],
                sub_df["theory_central"] + sub_df["scale_uncertainty_plus"],
                color=col, alpha=0.2
            )
        plt.xscale("log")
        plt.xlabel("Bjorken $x$")
        plt.ylabel("Reduced Cross Section $\sigma_{r, NC}^+$")
        plt.title("Theory Central Value and 7-Point Scale Uncertainty Band")
        plt.legend(loc='best', ncol=2, fontsize=9)
        plt.grid(True, which="both", ls=":")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "scale_uncertainty.svg"))
        plt.close()
        
    # Combined plot showing both PDF and Scale uncertainties separately and combined (added in quadrature)
    plt.figure(figsize=(11, 7))
    colors = plt.cm.plasma(np.linspace(0, 0.8, len(target_q2s)))
    for q2_val, col in zip(target_q2s, colors):
        sub_df = df[df["Q2"] == q2_val].sort_values("x")
        if sub_df.empty:
            continue
        tot_err = sub_df["Sigma"] * (np.sqrt(sub_df["stat"]**2 + sub_df["uncor"]**2) / 100.0)
        
        # Plot data
        plt.errorbar(
            sub_df["x"], sub_df["Sigma"], yerr=tot_err, 
            fmt='o', color=col, capsize=3, alpha=0.5, label=f"$Q^2 = {q2_val:.1f}$ GeV$^2$ (Data)"
        )
        # Plot central theory
        plt.plot(
            sub_df["x"], sub_df["theory_central"], '-', color=col, 
            linewidth=1.5, label=f"$Q^2 = {q2_val:.1f}$ GeV$^2$ (Theory)"
        )
        
        # Calculate quadrature sum
        quad_plus = np.sqrt(sub_df["pdf_uncertainty_plus"]**2 + sub_df["scale_uncertainty_plus"]**2)
        quad_minus = np.sqrt(sub_df["pdf_uncertainty_minus"]**2 + sub_df["scale_uncertainty_minus"]**2)
        
        plt.fill_between(
            sub_df["x"], 
            sub_df["theory_central"] - quad_minus,
            sub_df["theory_central"] + quad_plus,
            color=col, alpha=0.15
        )
        
    plt.xscale("log")
    plt.xlabel("Bjorken $x$")
    plt.ylabel("Reduced Cross Section $\sigma_{r, NC}^+$")
    plt.title("HERA Combined NC $e^+p$ DIS vs Theory with Quadrature Uncertainty Bands")
    plt.legend(loc='best', ncol=2, fontsize=8)
    plt.grid(True, which="both", ls=":")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "combined_uncertainties.svg"))
    plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HERA DIS validation with uncertainties tool")
    parser.add_argument("--dataset", required=True, help="Dataset ID, e.g., HERA1+2_NCep_920")
    parser.add_argument("--backend", required=True, choices=["apfel"], help="Theory backend")
    parser.add_argument("--order", required=True, choices=["LO", "NLO"], help="Perturbative QCD order")
    parser.add_argument("--pdf-set", required=True, help="LHAPDF set name")
    parser.add_argument("--pdf-member", type=int, default=0, help="LHAPDF member index")
    parser.add_argument("--q2-min", type=float, default=3.5, help="Q2 min kinematic cut")
    parser.add_argument("--pdf-uncertainty", action="store_true", help="Enable PDF uncertainties")
    parser.add_argument("--scale-variations", action="store_true", help="Enable scale uncertainties")
    parser.add_argument("--output", required=True, help="Base output directory")
    
    args = parser.parse_args()
    full_output_dir = os.path.join(args.output, args.dataset)
    
    run_uncertainty_pipeline(
        dataset_id=args.dataset,
        backend=args.backend,
        order=args.order,
        pdf_set=args.pdf_set,
        pdf_member=args.pdf_member,
        q2_min=args.q2_min,
        output_dir=full_output_dir,
        do_pdf_unc=args.pdf_uncertainty,
        do_scale_var=args.scale_variations
    )
