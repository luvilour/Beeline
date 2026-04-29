from BLRun.runner import Runner
import os
import subprocess
import pandas as pd


class DeepSEMRunner(Runner):

    def generateInputs(self):
        expr = pd.read_csv(
            os.path.join(self.input_dir, "ExpressionData.csv"),
            index_col=0
        )
        expr.to_csv(os.path.join(self.working_dir, "ExpressionData.csv"))

    def run(self):
        cmd = (
            f"docker run --rm"
            f" -v {self.working_dir}:/usr/working_dir"
            f" deepsem:base"
            f" python runDeepSEM.py"
        )
        subprocess.call(cmd, shell=True)

    def parseOutput(self):
        raw = pd.read_csv(os.path.join(self.working_dir, "outFile.txt"))

        # Normalize column names
        raw.columns = [c.strip() for c in raw.columns]

        # Try common possibilities
        if 'Gene1' not in raw.columns:
            if 'TF' in raw.columns:
                raw = raw.rename(columns={'TF': 'Gene1'})
            elif 'source' in raw.columns:
                raw = raw.rename(columns={'source': 'Gene1'})

        if 'Gene2' not in raw.columns:
            if 'Target' in raw.columns:
                raw = raw.rename(columns={'Target': 'Gene2'})
            elif 'target' in raw.columns:
                raw = raw.rename(columns={'target': 'Gene2'})

        if 'EdgeWeight' not in raw.columns:
            if 'Importance' in raw.columns:
                raw = raw.rename(columns={'Importance': 'EdgeWeight'})
            elif 'weight' in raw.columns:
                raw = raw.rename(columns={'weight': 'EdgeWeight'})

        # Now select
        raw = raw[['Gene1', 'Gene2', 'EdgeWeight']]
        raw['EdgeWeight'] = raw['EdgeWeight'].abs()

        raw.sort_values('EdgeWeight', ascending=False).to_csv(
            os.path.join(self.output_dir, "rankedEdges.csv"),
            index=False,
            sep='\t'
        )
