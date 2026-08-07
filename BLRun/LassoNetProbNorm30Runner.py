from BLRun.runner import Runner
import os
import subprocess
import pandas as pd

class LassoNetProbNorm30Runner(Runner):

    def generateInputs(self):
        # Doc: reads from self.input_dir, writes processed files to self.working_dir
        # Your ExpressionData.csv is already in the right format, so we just copy it
        expr = pd.read_csv(
            os.path.join(self.input_dir, "ExpressionData.csv"), index_col=0
        )
        expr.to_csv(os.path.join(self.working_dir, "ExpressionData.csv"))

    def run(self):
        # Doc: "constructs a docker run command, self.working_dir
        # is mounted as /usr/working_dir inside the container"
        cmd = (
            f"docker run --rm"
            f" -v {self.working_dir}:/usr/working_dir"
            f" lassonetprobnorm:base"
            f" python runLassoNetProbNorm.py --n_models 30"
        )
        subprocess.call(cmd, shell=True)

    def parseOutput(self):
        # Doc: "reads algorithm outputs and formats them into
        # self.output_dir/rankedEdges.csv with columns Gene1, Gene2, EdgeWeight"
        raw = pd.read_csv(os.path.join(self.working_dir, "outFile.txt"))
        raw = raw[['Gene1', 'Gene2', 'EdgeWeight']]
        raw['EdgeWeight'] = raw['EdgeWeight'].abs()
        raw.sort_values('EdgeWeight', ascending=False).to_csv(
            os.path.join(self.output_dir, "rankedEdges.csv"), index=False, sep='\t'
        )
