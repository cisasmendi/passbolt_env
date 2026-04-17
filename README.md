# Passbolt-dwn - Docker Client

Command-line client to interact with Passbolt from Docker. It allows listing and downloading resources using GPG authentication, with full support for custom fields and direct export to environment variables.

## Context and Motivation

This project was created in response to limitations found in **passbolt-cli**, especially in real-world operational scenarios:

- **Custom fields issue:**  
  `passbolt-cli` has problems correctly retrieving and processing custom fields from resources. This becomes a limitation when secrets are not limited to standard fields (username/password), but distributed across multiple keys (tokens, endpoints, configs, etc.).

- **Need for automation in production environments:**  
  In production servers, it is common to:
  - Inject credentials dynamically
  - Avoid hardcoding secrets
  - Integrate secrets into deployment pipelines

  However, there was no simple tool that could:
  - Download a complete resource from Passbolt
  - Automatically transform it into environment variables (`.env`)
  - Use it directly in processes like `docker run`, `docker-compose`, or shell scripts

- **Portability and isolation:**  
  Docker was chosen to avoid dependency issues, host GPG configuration complexity, and to simplify usage across different environments (CI/CD, VPS, clusters, etc.).

**Passbolt-dwn** solves these problems by:
- Accessing all resource fields (including custom ones)
- Exporting them into automation-ready formats
- Integrating easily into deployment and automation workflows

---

## Prerequisites

- Docker installed
- GPG private key configured in Passbolt
- Access to a Passbolt instance

## Configuration

1. **Copy the example configuration file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file with your credentials:**
   - `PASSBOLT_URL`: URL of your Passbolt instance
   - `PRIVATE_KEY`: Your full GPG private key
   - `PASSPHRASE`: Passphrase of your GPG key
   - `RESOURCE_ID`: (Optional) Default resource ID

---

## Build the Image

```bash
docker build -t passbolt-dwn .
```

---

## Usage

### 1. List Resources

```bash
docker run --rm -v ${PWD}/out:/app/out -v ${PWD}/private.key:/app/private.key --env-file .env passbolt-dwn --list
```

**Output:**
- Console list with ID, name, and URI of each resource
- `out/resources_list.json` file with the full list

---

### 2. Download Resource

#### JSON Format:
```bash
docker run --rm -v ${PWD}/out:/app/out -v ${PWD}/private.key:/app/private.key --env-file .env passbolt-dwn --download RESOURCE_ID -j
```

**Output:**
- `out/resource_RESOURCE_ID.json` file with all fields (including custom ones)

#### ENV Format:
```bash
docker run --rm -v ${PWD}/out:/app/out -v ${PWD}/private.key:/app/private.key --env-file .env passbolt-dwn --download RESOURCE_ID -e
```

**Output:**
- `out/resource_RESOURCE_ID.env` file ready to use with `source`, `docker --env-file`, or CI/CD pipelines

#### Both Formats:
```bash
docker run --rm -v ${PWD}/out:/app/out -v ${PWD}/private.key:/app/private.key --env-file .env passbolt-dwn --download RESOURCE_ID -j -e
```

---

## Common Use Cases

### Inject environment variables into containers

```bash
docker run --env-file out/resource_xxx.env my_app
```

### Use in deployment scripts

```bash
source out/resource_xxx.env
./deploy.sh
```

### CI/CD integration

- Fetch secrets at runtime
- Avoid storing them in repositories
- Centralize credentials in Passbolt

---

## Output File Structure

### JSON Format (`resource_ID.json`)
```json
{
  "field1": "value1",
  "field2": "value2",
  "_resource_name": "Resource Name",
  "_resource_id": "resource-uuid",
  "_resource_uri": "https://example.com"
}
```

### ENV Format (`resource_ID.env`)
```bash
# Resource variables: Resource Name
# Resource ID: resource-uuid
# Source: https://example.com

field1="value1"
field2="value2"
```

---

## Typical Workflow

1. List resources:
```bash
docker run --rm -v ${PWD}/out:/app/out -v ${PWD}/private.key:/app/private.key --env-file .env passbolt-dwn --list
```

2. Download a specific resource:
```bash
docker run --rm -v ${PWD}/out:/app/out -v ${PWD}/private.key:/app/private.key --env-file .env passbolt-dwn --download RESOURCE_ID -e
```

3. Use variables:
```bash
source out/resource_xxx.env
echo $field1
```

---

## Security

- Output files contain sensitive data
- Restrict permissions on the `out/` directory
- Do not commit `.env` files to version control
- Consider using Docker secrets or vault solutions in production

---

## Troubleshooting

### GPG authentication error
- Ensure the private key is complete in `PRIVATE_KEY`
- Verify the passphrase
- Confirm the key is associated with your Passbolt account

### Missing fields
- Ensure the resource has custom fields defined
- Verify access permissions

### Connection error
- Check `PASSBOLT_URL`
- Verify SSL configuration if needed
- Test network connectivity

### Resource not found
- Use `--list` to confirm existence
- Verify permissions
- Check `RESOURCE_ID`

---

## Help

```bash
docker run --rm passbolt-dwn --help
```
