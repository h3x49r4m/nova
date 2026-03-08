# {Workflow Name} Workflow

## Overview
{Brief description of the workflow's purpose and objectives. What does this workflow accomplish?}

## Prerequisites
List of required state files, conditions, and dependencies that must exist before this workflow can run.

### Required State Files
- `{state-file-1.md}` - {Description of file content and purpose}
- `{state-file-2.md}` - {Description of file content and purpose}

### Preconditions
- {Condition 1 that must be true}
- {Condition 2 that must be true}

### Dependencies
- `{skill-name}` (version >= X.Y.Z) - {Reason for dependency}
- `{skill-name}` (version >= X.Y.Z) - {Reason for dependency}

## Steps

### Step 1: {Step Name}
{Description of what this step accomplishes}

1. **{Sub-step 1}**
   - {Action to perform}
   - {Expected outcome}
   - {Files to read/write}

2. **{Sub-step 2}**
   - {Action to perform}
   - {Expected outcome}
   - {Files to read/write}

**Validation:** {How to verify this step completed successfully}

### Step 2: {Step Name}
{Description of what this step accomplishes}

1. **{Sub-step 1}**
   - {Action to perform}
   - {Expected outcome}
   - {Files to read/write}

2. **{Sub-step 2}**
   - {Action to perform}
   - {Expected outcome}
   - {Files to read/write}

**Validation:** {How to verify this step completed successfully}

### Step 3: {Step Name}
{Description of what this step accomplishes}

[Continue with additional steps as needed...]

## Error Handling

### Common Errors

#### Error: {Error Name}
- **Description:** {What causes this error}
- **Recovery:** {How to recover from this error}
- **Prevention:** {How to prevent this error in the future}

#### Error: {Error Name}
- **Description:** {What causes this error}
- **Recovery:** {How to recover from this error}
- **Prevention:** {How to prevent this error in the future}

### Rollback Scenarios

#### Scenario: {Scenario Name}
- **Trigger:** {What triggers the rollback}
- **Actions:** {List of rollback actions to perform}
- **Cleanup:** {How to clean up after rollback}

#### Scenario: {Scenario Name}
- **Trigger:** {What triggers the rollback}
- **Actions:** {List of rollback actions to perform}
- **Cleanup:** {How to clean up after rollback}

## State Contracts

### Read Contracts
The following state files are read during this workflow:
- `{state-file-1.md}` - {Why it's read and what information is extracted}
- `{state-file-2.md}` - {Why it's read and what information is extracted}

### Write Contracts
The following state files are written/updated during this workflow:
- `{state-file-1.md}` - {What information is written to this file}
- `{state-file-2.md}` - {What information is written to this file}

## Execution Flow

**Input Parameters:**
- `param1` (required) - {Description and expected format}
- `param2` (optional, default: `{default}`) - {Description and expected format}

**Output:**
- `output1` - {Description of output}
- `output2` - {Description of output}

**Flow:**
1. Validate input parameters
2. Read required state files
3. Execute Step 1
4. Execute Step 2
5. Execute Step 3
6. Write output state files
7. Return results

## Testing

### Test Cases

#### Test Case 1: {Test Name}
- **Description:** {What this test validates}
- **Setup:** {How to set up the test}
- **Input:** {Test input values}
- **Expected Output:** {Expected result}
- **Validation:** {How to verify the result}

#### Test Case 2: {Test Name}
- **Description:** {What this test validates}
- **Setup:** {How to set up the test}
- **Input:** {Test input values}
- **Expected Output:** {Expected result}
- **Validation:** {How to verify the result}

### Test Coverage
- Unit tests: {Percentage}% coverage
- Integration tests: {Percentage}% coverage
- End-to-end tests: {Percentage}% coverage

## Performance Considerations

### Expected Performance
- **Execution Time:** {Expected duration}
- **Memory Usage:** {Expected memory footprint}
- **I/O Operations:** {Number and type of I/O operations}

### Optimization Tips
- {Tip 1 for optimizing performance}
- {Tip 2 for optimizing performance}

## Security Considerations

### Security Checks
- {Security check 1 performed during workflow}
- {Security check 2 performed during workflow}

### Data Protection
- {How sensitive data is protected}
- {How access is controlled}

## Configuration

### Required Configuration
- `config_option_1` (required) - {Description and valid values}
- `config_option_2` (required) - {Description and valid values}

### Optional Configuration
- `config_option_3` (optional, default: `{default}`) - {Description and valid values}
- `config_option_4` (optional, default: `{default}`) - {Description and valid values}

## Monitoring and Logging

### Log Levels
- **INFO:** {What INFO messages are logged}
- **WARNING:** {What WARNING messages are logged}
- **ERROR:** {What ERROR messages are logged}

### Key Metrics
- `{metric_name}` - {Description and how it's measured}
- `{metric_name}` - {Description and how it's measured}

## Troubleshooting

### Issue: {Issue Name}
**Symptoms:** {What symptoms appear}
**Possible Causes:** {List of possible causes}
**Solutions:** {List of possible solutions}

### Issue: {Issue Name}
**Symptoms:** {What symptoms appear}
**Possible Causes:** {List of possible causes}
**Solutions:** {List of possible solutions}

## Examples

### Example 1: {Example Name}
**Scenario:** {Description of the scenario}
**Input:**
```python
# Example input
param1 = "value1"
param2 = "value2"
```
**Expected Output:**
```python
# Expected output
result = {
    "status": "success",
    "data": "output_data"
}
```

### Example 2: {Example Name}
**Scenario:** {Description of the scenario}
**Input:**
```python
# Example input
param1 = "value1"
```
**Expected Output:**
```python
# Expected output
result = {
    "status": "success",
    "data": "output_data"
}
```

## References

- Related documentation: `{link-or-file}`
- API documentation: `{link-or-file}`
- Design decisions: `{link-or-file}`

## Changelog

### Version {X.Y.Z} ({Date})
- **Added:** {New features or capabilities}
- **Changed:** {Changes to existing functionality}
- **Fixed:** {Bug fixes}
- **Deprecated:** {Features that will be removed in future versions}

### Version {X.Y.Z} ({Date})
- **Added:** {New features or capabilities}
- **Changed:** {Changes to existing functionality}
- **Fixed:** {Bug fixes}