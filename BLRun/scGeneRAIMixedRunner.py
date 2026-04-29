from BLRun.runner import Runner
import os
import subprocess
import pandas as pd

class scGeneRAIMixedRunner(Runner):

    def generateInputs(self):
        # Just copy ExpressionData.csv — scGeneRAI reads it directly
        expr = pd.read_csv(
            os.path.join(self.input_dir, "ExpressionData.csv"), index_col=0
        )
        expr.to_csv(os.path.join(self.working_dir, "ExpressionData.csv"))

    def run(self):
        cmd = (
            f"docker run --rm"
            f" -v '{self.working_dir}:/usr/working_dir'"
            f" scgeneraimixed:base"
            f" python runscGeneRAI.py"
        )
        subprocess.call(cmd, shell=True)

    def parseOutput(self):
        out_file = os.path.join(self.working_dir, "outFile.txt")

        if not os.path.exists(out_file):
            print("[ScGeneRAI] ERROR: outFile.txt not found — runScGeneRAI.py likely crashed.")
            return

        raw = pd.read_csv(out_file)
        raw = raw[['Gene1', 'Gene2', 'EdgeWeight']]
        raw['EdgeWeight'] = raw['EdgeWeight'].abs()
        raw.sort_values('EdgeWeight', ascending=False).to_csv(
            os.path.join(self.output_dir, "rankedEdges.csv"), index=False, sep='\t'
        )
