# Enroot

!!! note "Enroot Environment class"

    - [Read on GitHub](https://github.com/swe-agent/mini-swe-agent/blob/main/src/minisweagent/environments/enroot.py)

    ??? note "Full source code"

        ```python
        --8<-- "src/minisweagent/environments/enroot.py"
        ```

[Enroot](https://github.com/NVIDIA/enroot) is NVIDIA's container runtime designed for HPC environments. It provides unprivileged container execution without requiring root access, making it ideal for shared computing clusters.

## Usage

```bash
mini --environment-class enroot --environment.image docker://python:3.11-slim
```

Or in a YAML configuration file:

```yaml
environment:
  environment_class: enroot
  image: docker://python:3.11-slim
  cwd: /workspace
  writable: true
```

## Prerequisites

Enroot must be installed and available in your PATH. You can verify this with:

```bash
enroot version
```

::: minisweagent.environments.enroot

{% include-markdown "../../_footer.md" %}
