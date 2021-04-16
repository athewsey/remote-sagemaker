# Automating Code Execution on Amazon SageMaker

As well as many other features, [Amazon SageMaker](https://aws.amazon.com/sagemaker/) provides [Jupyter](https://jupyter.org/)-based data science notebook environments on the cloud in two flavours:

- [Classic SageMaker Notebook Instances](https://docs.aws.amazon.com/sagemaker/latest/dg/nbi.html), for a straightforward managed Jupyter/JupyterLab+conda experience
- [Amazon SageMaker Studio](https://aws.amazon.com/sagemaker/studio/), a fully integrated development environment (IDE) for machine learning: Extending JupyterLab with additional features and integrations

In either case, users may wish to automatically trigger the execution of code in SageMaker notebook environments - to customise the out-of-the-box setup or run any other required jobs or processes.

This repository demonstrates some basic code examples using the same [Jupyter Server REST API](https://github.com/jupyter/jupyter/wiki/Jupyter-Notebook-Server-API) and [Jupyter Client WebSocket API](https://jupyter-client.readthedocs.io/en/stable/messaging.html#) (plus some SageMaker Studio extensions). 

- **[SMStudio Remote Notebook.ipynb](SMStudio%20Remote%20Notebook.ipynb)**: Run all code cells of an (existing) notebook as a SageMaker Studio user
- **[SMStudio Remote Terminal.ipynb](SMStudio%20Remote%20Terminal.ipynb)**: Open a *System Terminal* and run commands as a SageMaker Studio user


## Related Tools

Many of the concepts in these examples are extensible and transferable (e.g. to classic NBIs), but in some settings alternative patterns may be more appropriate:

- To execute code on creation or start-up of a classic notebook instance, use [Lifecycle configuration scripts](https://docs.aws.amazon.com/sagemaker/latest/dg/notebook-lifecycle-config.html)
- For scheduling notebooks to "run" as parameterized SageMaker processing jobs, see [this AWS blog post with Papermill](https://aws.amazon.com/blogs/machine-learning/scheduling-jupyter-notebooks-on-sagemaker-ephemeral-instances/)


## A Note on Security

As these examples highlight, providing the IAM `sagemaker:CreatePresignedDomainUrl` (for Studio) and `sagemaker:CreatePresignedNotebookInstanceUrl` (for NBI) permissions is sufficient to grant login to the target SageMaker environment and also code execution on that environment.

For more information on conditions you can apply to scope down these permissions, refer to the [IAM reference for Amazon SageMaker](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonsagemaker.html).
