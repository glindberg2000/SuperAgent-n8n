# Troubleshooting Guide

**Common issues and solutions for SuperAgent n8n Discord bot.**

## Quick Diagnostics

### System Health Check
```bash
# Check all services
docker ps
curl http://localhost:5001/health
curl http://localhost:5678
python check_database.py
```

### Service Status
- **✅ Healthy**: All services running, bot responding
- **⚠️ Degraded**: Some services working, limited functionality  
- **❌ Failed**: Services down, bot not responding

## Common Issues

### 1. Bot Not Responding in Discord

**Symptoms**: Bot shows as online but doesn't respond to mentions

**Diagnosis**:
```bash
# Check Discord bot logs
# Look for connection errors or message filtering issues
```

**Solutions**:

1. **Verify Bot Permissions**:
   - Bot has "Read Messages", "Send Messages", "Use Slash Commands"
   - Bot can see the channel you're testing in
   - Bot role is above other roles that might restrict access

2. **Check Message Filtering**:
   - Use direct bot mention: `@BotName hello`
   - Try keyword trigger: `hey grok, are you there?`
   - Verify role mentions are working: `@RoleName test`

3. **Restart Discord Bot**:
   ```bash
   # Stop discord_forwarder.py (Ctrl+C)
   source .venv/bin/activate
   python discord_forwarder.py
   ```

### 2. n8n Workflow Errors

**Symptoms**: Bot forwards messages but n8n workflow fails

**Diagnosis**:
```bash
# Check n8n execution logs
docker logs superagent-n8n

# Check workflow status in n8n interface
open http://localhost:5678
```

**Solutions**:

1. **Verify Workflow is Active**:
   - Open n8n interface
   - Check workflow toggle is "Active"
   - Look for red error indicators on nodes

2. **Check PostgreSQL Credentials**:
   - Go to Settings → Credentials in n8n
   - Verify "SuperAgent PostgreSQL" credential
   - Test connection

3. **Restart n8n Container**:
   ```bash
   docker restart superagent-n8n
   ```

### 3. Python API Server Issues

**Symptoms**: n8n calls API but gets connection refused or 500 errors

**Diagnosis**:
```bash
# Test API server directly
curl http://localhost:5001/health

# Check API server logs
# Look for error messages in terminal running discord_api_server.py
```

**Solutions**:

1. **Check Server is Running**:
   ```bash
   # Should show Python process on port 5001
   lsof -i :5001
   ```

2. **Verify Environment Variables**:
   ```bash
   # Check .env file has all required variables
   grep -E "(DISCORD_TOKEN|XAI_API_KEY|POSTGRES)" .env
   ```

3. **Database Connection Issues**:
   ```bash
   # Test database connection
   python check_database.py
   
   # If fails, check PostgreSQL container
   docker logs superagent-n8n-postgres-1
   ```

4. **Restart API Server**:
   ```bash
   # Stop discord_api_server.py (Ctrl+C)
   source .venv/bin/activate
   python discord_api_server.py
   ```

### 4. Database Connection Problems

**Symptoms**: API server can't connect to PostgreSQL

**Diagnosis**:
```bash
# Check PostgreSQL container
docker ps | grep postgres

# Test database connection
python check_database.py

# Check database logs
docker logs superagent-n8n-postgres-1
```

**Solutions**:

1. **Verify PostgreSQL Container**:
   ```bash
   # Start PostgreSQL if not running
   docker-compose -f docker/docker-compose.yml up -d postgres
   ```

2. **Check Database Credentials**:
   - Verify .env file has correct POSTGRES_* variables
   - Ensure n8n credentials match .env values

3. **Reset Database**:
   ```bash
   # WARNING: This deletes all data
   docker-compose -f docker/docker-compose.yml down -v
   docker-compose -f docker/docker-compose.yml up -d
   ```

### 5. Grok4 API Issues

**Symptoms**: Bot responds with fallback messages or timeouts

**Diagnosis**:
```bash
# Check API server logs for Grok4 errors
# Look for "Grok4 API timeout" or "Grok4 API error" messages
```

**Solutions**:

1. **Verify API Key**:
   ```bash
   # Check XAI_API_KEY is set correctly
   echo $XAI_API_KEY
   ```

2. **Test API Key**:
   ```bash
   curl -H "Authorization: Bearer $XAI_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"model":"grok-4-latest","messages":[{"role":"user","content":"test"}]}' \
        https://api.x.ai/v1/chat/completions
   ```

3. **Check Rate Limits**:
   - Grok4 has rate limits that may cause temporary failures
   - System has automatic fallbacks for timeouts
   - Wait and try again if hitting rate limits

### 6. Memory/Context Issues

**Symptoms**: Bot doesn't remember previous conversation

**Diagnosis**:
```bash
# Check database for stored messages
python check_database.py

# Look for user and message records
```

**Solutions**:

1. **Verify Database Storage**:
   ```bash
   # Should show users and messages
   python check_database.py
   ```

2. **Check API Server Logs**:
   - Look for "Built context with X messages"
   - Verify conversation history is being retrieved

3. **Test Memory Manually**:
   ```
   @Bot my name is John
   @Bot what's my name?
   ```
   Bot should remember "John"

### 7. Docker Networking Issues

**Symptoms**: Services can't communicate with each other

**Diagnosis**:
```bash
# Check Docker networks
docker network ls

# Check container connectivity
docker ps
```

**Solutions**:

1. **Use Correct Hostnames**:
   - n8n to Python API: `host.docker.internal:5001`
   - Python API to PostgreSQL: `localhost:5436`

2. **Restart Docker Stack**:
   ```bash
   docker-compose -f docker/docker-compose.yml down
   docker-compose -f docker/docker-compose.yml up -d
   ```

## Error Messages

### Common Error Patterns

**"Connection refused"**:
- Service not running or wrong port
- Check service status and ports

**"Missing required fields"**:  
- Data parsing issue in API server
- Check n8n webhook data format

**"there is no parameter $1"**:
- PostgreSQL parameter binding issue (shouldn't occur in current version)
- Restart API server

**"Read timed out"**:
- Grok4 API timeout (normal, has fallback)
- No action needed

**"Method not allowed"**:
- Wrong HTTP method or endpoint
- Check n8n workflow configuration

## Monitoring Commands

### Service Status
```bash
# All Docker containers
docker ps

# API server process
ps aux | grep discord_api_server

# Port usage
lsof -i :5001  # API server
lsof -i :5678  # n8n
lsof -i :5436  # PostgreSQL
```

### Logs
```bash
# API server logs (live)
tail -f terminal_output

# n8n container logs
docker logs -f superagent-n8n

# PostgreSQL logs
docker logs superagent-n8n-postgres-1

# Discord bot logs (live)
tail -f terminal_output
```

### Database Inspection
```bash
# Check database contents
python check_database.py

# Manual database connection
docker exec -it superagent-n8n-postgres-1 psql -U superagent -d superagent
```

## Performance Issues

### Slow Response Times

**Diagnosis**:
- Check API server logs for timing information
- Monitor Grok4 API response times

**Solutions**:
- Reduce conversation history limit in API server
- Check network connectivity
- Consider upgrading Grok4 API plan

### High Memory Usage

**Diagnosis**:
```bash
# Check container memory usage
docker stats

# Check Python process memory
ps aux | grep python
```

**Solutions**:
- Restart Python services periodically
- Reduce conversation history retention
- Monitor for memory leaks

## Getting Help

### Log Collection
When reporting issues, include:
1. **Service Status**: `docker ps` output
2. **API Health**: `curl http://localhost:5001/health`
3. **Database Status**: `python check_database.py` output
4. **Error Logs**: Relevant log excerpts
5. **Environment**: OS, Docker version, Python version

### Debug Mode
Enable verbose logging:
```python
# In discord_api_server.py
app.run(host='0.0.0.0', port=5001, debug=True)
```

### Community Support
- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check other docs for configuration details
- **Discord Community**: Join relevant Discord servers for help

Most issues can be resolved by restarting services and checking configuration. The system is designed to be resilient and self-recovering in most cases. 🚀