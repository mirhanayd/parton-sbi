import os
import ssl
import urllib.request
import hashlib

# Expected checksum for HERA1+2_NCep_920.dat
HERA_NC_920_SHA256 = "dfa2fba16fa490600d10b7125189676343f07b40787d41a74a2d29d30fd8a8bc"
DATA_URL = "https://www.desy.de/h1zeus/herapdf20/HERA1+2_NCep_920.dat"

def get_file_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def download_dataset(dest_dir="data/hepdata"):
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, "HERA1+2_NCep_920.dat")
    
    # If file exists, check checksum
    if os.path.exists(dest_path):
        current_checksum = get_file_sha256(dest_path)
        if current_checksum == HERA_NC_920_SHA256:
            print(f"Dataset already downloaded and verified: {dest_path}")
            return dest_path
        else:
            print(f"Checksum mismatch for existing file {dest_path}. Expected: {HERA_NC_920_SHA256}, got: {current_checksum}. Re-downloading...")
            os.remove(dest_path)
            
    print(f"Downloading from {DATA_URL}...")
    
    # Create unverified context to bypass local SSL certificate issue if any
    context = ssl._create_unverified_context()
    
    req = urllib.request.Request(
        DATA_URL,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    
    try:
        with urllib.request.urlopen(req, context=context) as response:
            content = response.read()
            
        with open(dest_path, "wb") as f:
            f.write(content)
            
        # Verify checksum of downloaded file
        downloaded_checksum = get_file_sha256(dest_path)
        if downloaded_checksum != HERA_NC_920_SHA256:
            raise ValueError(f"Downloaded file checksum mismatch! Expected: {HERA_NC_920_SHA256}, got: {downloaded_checksum}")
            
        print(f"Successfully downloaded and verified HERA data to {dest_path}")
        return dest_path
        
    except Exception as e:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise RuntimeError(f"Failed to download and verify dataset: {e}")

if __name__ == "__main__":
    download_dataset()
