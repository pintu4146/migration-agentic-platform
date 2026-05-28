# Server-Sent Events (SSE) Implementation

## Overview

Replaced polling-based state updates with Server-Sent Events (SSE) for real-time workflow state updates.

## Architecture

### Backend (FastAPI)

**Endpoint:** `GET /api/orchestration/stream/{project_id}`

**Implementation:** `backend/app/api/orchestration.py`

```python
@router.get("/stream/{project_id}")
async def stream_workflow_state(project_id: str):
    """
    Server-Sent Events endpoint for real-time workflow state updates.
    Streams workflow state changes to the client in real-time.
    """
```

**Features:**
- Async event generator
- Checks for state updates every second
- Only sends updates when state version changes
- Automatic error handling and recovery
- Proper SSE formatting with event types

**Headers:**
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no` (disables nginx buffering)

### Frontend (React)

**Hook:** `frontend/src/hooks/useWorkflowSSE.js`

**Usage:**
```javascript
const { state, loading, error, isConnected, refetch } = useWorkflowSSE(projectId);
```

**Features:**
- Uses browser's native EventSource API
- Automatic reconnection on disconnect (5-second delay)
- Connection status tracking
- Error handling
- Cleanup on unmount
- Manual refetch capability

**Event Types:**
- `state_update` - New workflow state
- `error` - Server-side errors

## Benefits Over Polling

### Efficiency
- ❌ **Polling:** HTTP request every 2 seconds = 30 requests/minute
- ✅ **SSE:** Single persistent connection = 1 connection

### Real-Time Updates
- ❌ **Polling:** Up to 2-second delay
- ✅ **SSE:** Instant updates (< 1 second)

### Server Load
- ❌ **Polling:** Constant HTTP overhead
- ✅ **SSE:** Minimal overhead after connection

### Bandwidth
- ❌ **Polling:** Full HTTP headers on every request
- ✅ **SSE:** Headers only on initial connection

### Scalability
- ❌ **Polling:** Linear increase in requests with users
- ✅ **SSE:** Efficient connection pooling

## UI Indicators

### Connected State
```
⚡ Live Updates
```
- Green color (`var(--cds-support-02)`)
- Pulsing animation
- Indicates active SSE connection

### Disconnected State
```
⚠️ Reconnecting...
```
- Yellow/warning color (`var(--cds-support-03)`)
- Shows when connection is lost
- Automatic reconnection in progress

## Error Handling

### Connection Errors
- Automatic reconnection after 5 seconds
- User-friendly error messages
- Connection status indicator

### Server Errors
- Sent as `error` events
- Displayed in UI
- Logged to console

### Network Issues
- EventSource handles reconnection automatically
- Manual reconnection logic as fallback
- Graceful degradation

## Testing

### Start Backend
```bash
cd backend
python -m uvicorn app.main:app --reload
```

### Start Frontend
```bash
cd frontend
npm run dev
```

### Test SSE Connection
1. Open browser DevTools → Network tab
2. Filter by "EventStream" or "stream"
3. Start a workflow
4. Observe SSE connection and events
5. Execute workflow steps
6. Watch real-time state updates

### Console Logs
- `SSE: Connecting to...` - Connection initiated
- `SSE: Connected to {projectId}` - Connection established
- `SSE: Received state update` - State update received
- `SSE: Connection error` - Connection lost
- `SSE: Attempting to reconnect` - Reconnection started

## Migration from Polling

### Removed Files
- `frontend/src/hooks/useWorkflowPolling.js` (can be deleted)

### Updated Files
- `backend/app/api/orchestration.py` - Added SSE endpoint
- `frontend/src/hooks/useWorkflowSSE.js` - New SSE hook
- `frontend/src/pages/WorkflowExecution.jsx` - Uses SSE instead of polling
- `frontend/src/pages/WorkflowExecution.scss` - Updated indicator styles

### Breaking Changes
None - API is backward compatible. The old polling endpoint still exists.

## Browser Support

SSE is supported in all modern browsers:
- ✅ Chrome/Edge (all versions)
- ✅ Firefox (all versions)
- ✅ Safari (all versions)
- ❌ Internet Explorer (not supported)

## Production Considerations

### Nginx Configuration
```nginx
location /api/orchestration/stream/ {
    proxy_pass http://backend;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
    proxy_buffering off;
    proxy_cache off;
}
```

### Load Balancing
- Use sticky sessions for SSE endpoints
- Or implement Redis pub/sub for multi-server deployments

### Monitoring
- Track active SSE connections
- Monitor connection duration
- Alert on high reconnection rates

## Future Enhancements

1. **Heartbeat Messages** - Send periodic pings to keep connection alive
2. **Selective Updates** - Only send changed fields, not full state
3. **Compression** - Compress event data for large states
4. **Authentication** - Add token-based auth for SSE connections
5. **Rate Limiting** - Limit connections per user/IP

## Troubleshooting

### Connection Keeps Dropping
- Check firewall/proxy settings
- Verify nginx configuration
- Check server timeout settings

### No Updates Received
- Verify state is actually changing
- Check backend logs for errors
- Confirm EventSource is connected

### High CPU Usage
- Reduce check interval in backend (currently 1 second)
- Implement change detection instead of polling state
- Use Redis pub/sub for state changes

## Made with Bob