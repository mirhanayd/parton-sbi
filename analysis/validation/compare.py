import os
import sys
import json
import argparse
import subprocess
import concurrent.futures
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Add parent directory to sys.path so we can import from analysis
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hepdata.download import download_dataset
from hepdata.parse import parse_dataset
from hepdata.schemas import validate_metadata
from validation.binning import apply_cuts
from validation.covariance import build_covariance_matrix
from validation.chi_square import calculate_chi2_uncorrelated, calculate_chi2_covariance

def get_apfel_cli_path():
    # Allow overriding via environment variable
    backend_path = os.environ.get("APFEL_BACKEND_BIN")
    if backend_path and os.path.exists(backend_path):
        return backend_path
        
    # Check default location relative to project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    default_path = os.path.join(project_root, "physics-engine/build/apfel_cli")
    if os.path.exists(default_path):
        return default_path
        
    return "apfel_cli" # Fallback to PATH

def call_apfel_single(args_tuple):
    x, q2, pdf_set, pdf_member, order, apfel_bin = args_tuple
    
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
    
    try:
        proc = subprocess.Popen(
            [apfel_bin],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input=json.dumps(request))
        
        try:
            res = json.loads(stdout)
        except Exception:
            res = None

        if res is not None:
            if not res.get("success"):
                err = res.get("error", {})
                raise RuntimeError(f"APFEL++ error [code={err.get('code')}]: {err.get('message')} - Hint: {err.get('hint')}")
            return float(res["f2"]), float(res["fl"])
        else:
            if proc.returncode != 0:
                raise RuntimeError(f"apfel_cli returned exit code {proc.returncode}. Stderr: {stderr.strip()}")
            raise RuntimeError("apfel_cli returned empty stdout.")
    except Exception as e:
        raise RuntimeError(f"Error evaluating point (x={x}, Q2={q2}): {e}")

def run_comparison(dataset_id, backend, order, pdf_set, pdf_member, q2_min, output_dir):
    print("=" * 60)
    print("HERA Validation Pipeline Running")
    print("=" * 60)
    print(f"Dataset:      {dataset_id}")
    print(f"Backend:      {backend}")
    print(f"Order:        {order}")
    print(f"PDF Set:      {pdf_set} (member {pdf_member})")
    print(f"Q2 Min Cut:   {q2_min} GeV^2")
    print(f"Output Dir:   {output_dir}")
    print("-" * 60)
    
    # 1. Download and Parse HERA Data
    data_file = download_dataset()
    df_raw = parse_dataset(data_file)
    print(f"Parsed {len(df_raw)} raw data points.")
    
    # 2. Apply Kinematic Cuts
    df = apply_cuts(df_raw, q2_min=q2_min)
    n_points = len(df)
    print(f"Applied cuts. Remaining points: {n_points}")
    if n_points == 0:
        raise ValueError("No data points remaining after kinematic cuts.")
        
    # 3. Call APFEL++ to get F2 and FL
    apfel_bin = get_apfel_cli_path()
    print(f"Using APFEL backend: {apfel_bin}")
    
    tasks = []
    for idx, row in df.iterrows():
        tasks.append((row["x"], row["Q2"], pdf_set, pdf_member, order, apfel_bin))
        
    print("Evaluating structure functions in parallel...")
    f2_list = []
    fl_list = []
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(call_apfel_single, tasks))
        
    for f2_val, fl_val in results:
        f2_list.append(f2_val)
        fl_list.append(fl_val)
        
    df["F2_theory"] = f2_list
    df["FL_theory"] = fl_list
    
    # 4. Calculate Theoretical Reduced Cross Section
    # sigma_r = F2 - (y^2 / Y_+) * FL
    # Y_+ = 1 + (1 - y)^2
    df["y_plus"] = 1.0 + (1.0 - df["y"])**2
    df["Sigma_theory"] = df["F2_theory"] - (df["y"]**2 / df["y_plus"]) * df["FL_theory"]
    
    # 5. Build Covariance Matrix and Perform Chi2 Analysis
    cov = build_covariance_matrix(df)
    
    # Uncorrelated Chi2
    chi2_uncor, pulls_uncor = calculate_chi2_uncorrelated(
        df["Sigma"].values,
        df["Sigma_theory"].values,
        df["stat"].values,
        df["uncor"].values
    )
    
    # Covariance (Full) Chi2
    chi2_cov, pulls_cov = calculate_chi2_covariance(
        df["Sigma"].values,
        df["Sigma_theory"].values,
        cov
    )
    
    ndf = n_points
    chi2_per_ndf_uncor = chi2_uncor / ndf
    chi2_per_ndf_cov = chi2_cov / ndf
    
    print(f"Uncorrelated Chi2: {chi2_uncor:.3f} / {ndf} NDF = {chi2_per_ndf_uncor:.3f}")
    print(f"Full Covariance Chi2: {chi2_cov:.3f} / {ndf} NDF = {chi2_per_ndf_cov:.3f}")
    
    # Add values to dataframe
    df["pull_uncor"] = pulls_uncor
    df["pull_cov"] = pulls_cov
    df["ratio"] = df["Sigma"] / df["Sigma_theory"]
    df["residual"] = df["Sigma"] - df["Sigma_theory"]
    
    # Calculate stats
    mean_ratio = float(df["ratio"].mean())
    max_pull = float(np.max(np.abs(pulls_cov)))
    
    # 6. Generate Metadata & Config JSONs
    os.makedirs(output_dir, exist_ok=True)
    
    metadata = {
        "dataset_id": dataset_id,
        "name": "HERA Combined DIS NC e+p 920 GeV",
        "description": "HERA combined reduced cross sections NC e+p scattering at E_p = 920 GeV, E_e = 27.5 GeV (Table 1 / HERA1+2_NCep_920.dat)",
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
        "chi_square_uncorrelated": float(chi2_uncor),
        "chi_square": float(chi2_cov),
        "degrees_of_freedom": ndf,
        "chi_square_per_ndf": float(chi2_per_ndf_cov),
        "mean_ratio": mean_ratio,
        "maximum_absolute_pull": max_pull,
        "data_source": "HERA1+2_NCep_920.dat",
        "theory_configuration": theory_config
    }
    
    # Save outputs
    with open(os.path.join(output_dir, "dataset_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    with open(os.path.join(output_dir, "theory_config.json"), "w") as f:
        json.dump(theory_config, f, indent=2)
    with open(os.path.join(output_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
        
    df.to_csv(os.path.join(output_dir, "comparison.csv"), index=False)
    
    # Also save as comparison.json
    records = df.to_dict(orient="records")
    with open(os.path.join(output_dir, "comparison.json"), "w") as f:
        json.dump(records, f, indent=2)
        
    # 7. Plots Generation
    generate_plots(df, output_dir)
    print(f"Validation outputs successfully saved to {output_dir}")
    print("=" * 60)

def generate_plots(df, output_dir):
    # Set style
    plt.rcParams.update({
        'font.size': 11,
        'axes.labelsize': 12,
        'axes.titlesize': 13,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'figure.titlesize': 14
    })
    
    # For plotting, select a few representative Q2 bins to avoid a messy plot
    unique_q2 = sorted(df["Q2"].unique())
    # Choose 6 representative scales
    target_q2s = [unique_q2[i] for i in np.linspace(0, len(unique_q2)-1, 6, dtype=int)]
    
    # 1. Data vs Theory Plot
    plt.figure(figsize=(10, 7))
    colors = plt.cm.plasma(np.linspace(0, 0.8, len(target_q2s)))
    
    for q2_val, col in zip(target_q2s, colors):
        sub_df = df[df["Q2"] == q2_val].sort_values("x")
        if sub_df.empty:
            continue
        # stat and uncor are in percent relative to Sigma
        tot_err = sub_df["Sigma"] * (np.sqrt(sub_df["stat"]**2 + sub_df["uncor"]**2) / 100.0)
        
        plt.errorbar(
            sub_df["x"], sub_df["Sigma"], yerr=tot_err, 
            fmt='o', color=col, capsize=3, label=f"$Q^2 = {q2_val:.1f}$ GeV$^2$ (Data)"
        )
        plt.plot(
            sub_df["x"], sub_df["Sigma_theory"], '-', color=col, 
            label=f"$Q^2 = {q2_val:.1f}$ GeV$^2$ (Theory)"
        )
        
    plt.xscale("log")
    plt.yscale("linear")
    plt.xlabel("Bjorken $x$")
    plt.ylabel("Reduced Cross Section $\sigma_{r, NC}^+$")
    plt.title("HERA Combined NC $e^+p$ DIS vs Theory")
    plt.legend(loc='best', ncol=2, fontsize=9)
    plt.grid(True, which="both", ls=":")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "data_vs_theory.svg"))
    plt.close()
    
    # 2. Ratio Plot (Data / Theory)
    plt.figure(figsize=(10, 6))
    for q2_val, col in zip(target_q2s, colors):
        sub_df = df[df["Q2"] == q2_val].sort_values("x")
        if sub_df.empty:
            continue
        tot_err_rel = np.sqrt(sub_df["stat"]**2 + sub_df["uncor"]**2) / 100.0
        
        plt.errorbar(
            sub_df["x"], sub_df["ratio"], yerr=tot_err_rel * sub_df["ratio"], 
            fmt='o', color=col, capsize=3, label=f"$Q^2 = {q2_val:.1f}$ GeV$^2$"
        )
    plt.axhline(1.0, color='red', linestyle='--')
    plt.xscale("log")
    plt.xlabel("Bjorken $x$")
    plt.ylabel("Data / Theory Ratio")
    plt.title("Data / Theory Ratio")
    plt.legend(loc='best', ncol=2, fontsize=9)
    plt.grid(True, which="both", ls=":")
    plt.ylim(0.7, 1.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "ratio.svg"))
    plt.close()
    
    # 3. Residuals Plot (Data - Theory)
    plt.figure(figsize=(10, 5))
    plt.axhline(0.0, color='red', linestyle='--')
    plt.scatter(df["x"], df["residual"], c=df["Q2"], cmap='plasma', alpha=0.7, edgecolors='none')
    cbar = plt.colorbar()
    cbar.set_label("$Q^2$ [GeV$^2$]")
    plt.xscale("log")
    plt.xlabel("Bjorken $x$")
    plt.ylabel("Residual (Data - Theory)")
    plt.title("Residuals (Data - Theory) vs Bjorken $x$")
    plt.grid(True, which="both", ls=":")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "residuals.svg"))
    plt.close()
    
    # 4. Pulls Plot
    plt.figure(figsize=(10, 5))
    plt.axhline(0.0, color='black', linestyle='-')
    plt.axhline(2.0, color='red', linestyle='--')
    plt.axhline(-2.0, color='red', linestyle='--')
    plt.scatter(df["x"], df["pull_cov"], c=df["Q2"], cmap='plasma', alpha=0.7, edgecolors='none')
    cbar = plt.colorbar()
    cbar.set_label("$Q^2$ [GeV$^2$]")
    plt.xscale("log")
    plt.xlabel("Bjorken $x$")
    plt.ylabel("Pull (Covariance)")
    plt.title("Pulls vs Bjorken $x$")
    plt.grid(True, which="both", ls=":")
    plt.ylim(-5, 5)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "pulls.svg"))
    plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HERA DIS validation tool")
    parser.add_argument("--dataset", required=True, help="Dataset ID, e.g., HERA1+2_NCep_920")
    parser.add_argument("--backend", required=True, choices=["apfel"], help="Theory backend")
    parser.add_argument("--order", required=True, choices=["LO", "NLO"], help="Perturbative QCD order")
    parser.add_argument("--pdf-set", required=True, help="LHAPDF set name")
    parser.add_argument("--pdf-member", type=int, default=0, help="LHAPDF member index")
    parser.add_argument("--q2-min", type=float, default=3.5, help="Q2 min kinematic cut")
    parser.add_argument("--output", required=True, help="Base output directory")
    
    args = parser.parse_args()
    
    # Calculate full output path (outputs/validation/<dataset_name>)
    full_output_dir = os.path.join(args.output, args.dataset)
    
    try:
        run_comparison(
            dataset_id=args.dataset,
            backend=args.backend,
            order=args.order,
            pdf_set=args.pdf_set,
            pdf_member=args.pdf_member,
            q2_min=args.q2_min,
            output_dir=full_output_dir
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
