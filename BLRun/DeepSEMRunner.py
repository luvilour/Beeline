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

        raw = raw[['Gene1', 'Gene2', 'EdgeWeight']]
        raw['EdgeWeight'] = raw['EdgeWeight'].abs()

        raw.sort_values('EdgeWeight', ascending=False).to_csv(
            os.path.join(self.output_dir, "rankedEdges.csv"),
            index=False,
            sep='\t'
        )
