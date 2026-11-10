# Usage: .\tools\run_nb.ps1 <builder.py> <notebook.ipynb>
param([string]$Builder, [string]$Notebook)
$env:MLFLOW_DISABLE_AGENT_HINT = "1"
& .\.venv\Scripts\python.exe $Builder $Notebook
if (-not $?) { exit 1 }
& .\.venv\Scripts\jupyter.exe nbconvert --to notebook --execute --inplace $Notebook --ExecutePreprocessor.timeout=900 --log-level=ERROR 2>&1 | Select-Object -Last 25
