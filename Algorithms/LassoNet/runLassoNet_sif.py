from BLRun.runner import Runner
import os
import subprocess
import pandas as pd


# The BEELINE_SIF_DIR environment variable is set by the SLURM script.
# It points to the directory containing all .sif images.
# Falls back to a relative path for local testing.
SIF_DIR = os.environ.get("BEELINE_SIF_DIR", os.path.join(os.path.dirname(__file__), "../utils/sif_images"))


class LassoNetRunner(Runner):

    def generateInputs(self):
        expr = pd.read_csv(
            os.path.join(self.input_dir, "ExpressionData.csv"), index_col=0
        )
        expr.to_csv(os.path.join(self.working_dir, "ExpressionData.csv"))

    def run(self):
        print("before the running")
        sif = os.path.join(SIF_DIR, "lassonet_base.sif")
        cmd = (
            f"apptainer exec"
            f" --bind {self.working_dir}:/usr/working_dir"
            f" {sif}"
            f" python /runLassoNet.py"
        )
        subprocess.call(cmd, shell=True)

    def parseOutput(self):
        raw = pd.read_csv(os.path.join(self.working_dir, "outFile.txt"))
        raw = raw[['Gene1', 'Gene2', 'EdgeWeight']]
        raw['EdgeWeight'] = raw['EdgeWeight'].abs()
        raw.sort_values('EdgeWeight', ascending=False).to_csv(
            os.path.join(self.output_dir, "rankedEdges.csv"), index=False, sep='\t'
        )
