# Testing Enroot Environment

This guide explains how to test the enroot environment implementation for mini-swe-agent.

## Prerequisites

1. **Enroot installed**: Verify with `enroot version`
2. **Network access**: To pull Docker images from Docker Hub
3. **OpenAI API key** (for SWE-bench tests): `export OPENAI_API_KEY=your_key`

## Quick Verification

### 1. Basic Module Import Test

```bash
# Activate your virtual environment
source .venv/bin/activate

# Test module import
python -c "
from minisweagent.environments.enroot import EnrootEnvironment, EnrootEnvironmentConfig
print('Import successful')
c = EnrootEnvironmentConfig(image='docker://python:3.11-slim')
print(f'Config: image={c.image}, cwd={c.cwd}, timeout={c.timeout}')
"
```

### 2. Basic Container Test

```bash
python -c "
from minisweagent.environments.enroot import EnrootEnvironment

print('Creating enroot environment...')
env = EnrootEnvironment(image='docker://python:3.11-slim')
print('Container created!')

# Test basic command
result = env.execute('echo hello world')
print(f'Echo test: {result}')
assert result['returncode'] == 0
assert 'hello world' in result['output']

# Test Python execution
result = env.execute('python --version')
print(f'Python version: {result}')
assert result['returncode'] == 0

# Test working directory
result = env.execute('pwd', cwd='/tmp')
print(f'Working directory: {result}')
assert '/tmp' in result['output']

env.cleanup()
print('All basic tests passed!')
"
```

### 3. Environment Variables Test

```bash
python -c "
from minisweagent.environments.enroot import EnrootEnvironment

env = EnrootEnvironment(
    image='docker://python:3.11-slim',
    env={'MY_VAR': 'test_value', 'ANOTHER_VAR': 'another_value'}
)

result = env.execute('echo \$MY_VAR \$ANOTHER_VAR')
print(f'Env vars: {result}')
assert 'test_value another_value' in result['output']

env.cleanup()
print('Environment variable test passed!')
"
```

## Running Unit Tests

```bash
# Run all enroot tests (requires enroot to be installed)
pytest tests/environments/test_enroot.py -v

# Run only quick tests (skip slow image-pulling tests)
pytest tests/environments/test_enroot.py -v -m "not slow"

# Run with verbose output
pytest tests/environments/test_enroot.py -v -s
```

## SWE-bench Integration Test

### Single Instance Test

```bash
# Test with a single SWE-bench instance
mini-extra swebench-single \
    --subset verified \
    --split test \
    --model openai/gpt-5 \
    --environment-class enroot \
    -i 0 \
    --exit-immediately
```

### Batch Mode Test (1-3 instances)

```bash
# Test batch mode with first 3 instances
mini-extra swebench \
    --subset verified \
    --split test \
    --model openai/gpt-5 \
    --environment-class enroot \
    --slice 0:3 \
    --workers 1 \
    -o ./enroot_test_output
```

## Configuration Options

### EnrootEnvironmentConfig Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `image` | (required) | Container image URI (e.g., `docker://python:3.11-slim`) |
| `cwd` | `/` | Working directory for command execution |
| `env` | `{}` | Environment variables to set in container |
| `forward_env` | `[]` | Host environment variables to forward |
| `timeout` | `30` | Command execution timeout (seconds) |
| `executable` | `enroot` | Path to enroot executable |
| `import_timeout` | `300` | Timeout for importing images (seconds) |
| `create_timeout` | `120` | Timeout for creating containers (seconds) |
| `writable` | `True` | Make container filesystem writable |
| `root` | `False` | Run as root inside container |

### Environment Variable Override

```bash
# Use custom enroot executable
export MSWEA_ENROOT_EXECUTABLE=/path/to/enroot
```

## YAML Configuration

Create a config file (e.g., `enroot_config.yaml`):

```yaml
environment:
  environment_class: enroot
  image: docker://python:3.11-slim
  cwd: /workspace
  timeout: 60
  writable: true
  env:
    PAGER: cat
    TERM: xterm

model:
  model_name: openai/gpt-5

agent:
  step_limit: 100
  cost_limit: 5.0
```

Use it:

```bash
mini -c enroot_config.yaml
```

## Troubleshooting

### Common Issues

1. **"enroot: command not found"**
   - Install enroot or set `MSWEA_ENROOT_EXECUTABLE` to the correct path

2. **Image import fails with permission errors**
   - Check if you have write access to `/tmp` or set `ENROOT_CACHE_PATH`
   - Verify network connectivity to Docker Hub

3. **Container creation fails**
   - Check disk space for container storage
   - Verify enroot data directory permissions

4. **Commands timeout**
   - Increase `timeout` parameter
   - Check if the container is running correctly with `enroot list`

### Debug Mode

Enable debug logging:

```bash
export MSWEA_LOG_LEVEL=DEBUG
mini-extra swebench-single --environment-class enroot ...
```

### Manual Cleanup

If containers are left behind:

```bash
# List all enroot containers
enroot list

# Remove specific container
enroot remove -f minisweagent-XXXXXXXX

# Remove all minisweagent containers
enroot list | grep minisweagent | xargs -r enroot remove -f
```

## Expected Test Results

When all tests pass, you should see:

1. **Module import**: No errors
2. **Basic container test**: "All basic tests passed!"
3. **Unit tests**: All tests pass (or skip if enroot not available)
4. **SWE-bench test**: Agent starts and executes commands in the container

The enroot environment is working correctly if:
- Container is created successfully
- Commands execute and return correct output
- Environment variables are passed correctly
- Working directory changes work
- Cleanup removes the container
