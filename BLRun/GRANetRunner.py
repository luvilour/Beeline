from BLRun.runner import Runner
import os
import subprocess
import pandas as pd


class GRANetRunner(Runner):

    def generateInputs(self):
        """
        Copy ExpressionData.csv into the working directory.
        Also copies refNetwork.csv if available — used to restrict TF/target sets.
        If absent, GRANet will treat all genes as TFs and targets (fully connected).
        """
        expr = pd.read_csv(
            os.path.join(self.input_dir, "ExpressionData.csv"),
            index_col=0
        )
        expr.to_csv(os.path.join(self.working_dir, "ExpressionData.csv"))

        net_src = os.path.join(self.input_dir, "refNetwork.csv")
        if os.path.exists(net_src):
            net = pd.read_csv(net_src)
            net = net[['Gene1', 'Gene2']]
            net.to_csv(os.path.join(self.working_dir, "network.csv"), index=False)
        # If absent, no network.csv is written — runGRANet.py will detect this
        # and fall back to a fully connected all-gene graph

    def run(self):
        cmd = (
            f"docker run --rm"
            f" -v {self.working_dir}:/usr/working_dir"
            f" granet:base"
            f" python runGRANet.py"
        )
        subprocess.call(cmd, shell=True)

    def parseOutput(self):
        out_path = os.path.join(self.working_dir, "outFile.txt")
        if not os.path.exists(out_path):
            raise FileNotFoundError(
                f"GRANet produced no output at {out_path}. "
                "Check the Docker logs for training errors."
            )

        raw = pd.read_csv(out_path)
        raw = raw[['Gene1', 'Gene2', 'EdgeWeight']]
        raw['EdgeWeight'] = raw['EdgeWeight'].abs()

        raw.sort_values('EdgeWeight', ascending=False).to_csv(
            os.path.join(self.output_dir, "rankedEdges.csv"),
            index=False,
            sep='\t'
        )
