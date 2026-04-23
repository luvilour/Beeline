import pandas as pd
import sys

def main(input_path, output_path):
    expr = pd.read_csv(input_path, sep='\t', index_col=None)
    expr = expr.T
    expr.columns = ['Cell' + str(i+1) for i in range(expr.shape[1])]

    expr.index.name = 'Gene'
    
    expr.to_csv(output_path, sep='\t')
    print(f"Done: {input_path} -> {output_path}")

if __name__ == "__main__":
    input_path = sys.argv[1]
    output_path = sys.argv[2]

    main(input_path, output_path)
