LEXIPATH EXPERIMENT NOTEBOOK

LexiPath_Experiments.ipynb contains seven executed code cells with embedded outputs.
Open it in Jupyter or VS Code, using the project's Python environment. The numeric
libraries are already listed in requirements-lock.txt; a notebook editor/kernel
is a separate optional tool and is not required to run the tutoring application.

The notebook can run from the project root or the notebooks directory. It reads
saved TRAIN/DEV experiment JSON outputs and writes PNGs to outputs/presentation_plots.
It does not fit estimators, alter model selection, open TEST examples or modify
student databases. Source fit iterations/times are printed from the recorded audit.
Final DEV accuracy/loss comparisons must not be presented as epoch-wise training curves.

The stored outputs were executed in a shared project-Python namespace and captured
into standard notebook output cells. No Jupyter kernel installation is claimed.
