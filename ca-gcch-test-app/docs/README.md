# Azure Communication Services - Python Application

This is a Python conversion of the TypeScript Azure Communication Services Call Automation application. It provides comprehensive call management features including outbound calls, media streaming, recording, participant management, and real-time event handling.

## Features

### Call Management
- ✅ **Outbound PSTN Calls** - Place calls to phone numbers
- ✅ **Outbound ACS Calls** - Place calls to Azure Communication Services users
- ✅ **Group Calls** - Create multi-participant calls
- ✅ **Call Termination** - End calls for individual participants or everyone
- ✅ **Incoming Call Handling** - Answer incoming calls automatically

### Media Operations
- ✅ **Play Media** - Play audio files to all participants or specific targets
- ✅ **Media Streaming** - Real-time audio streaming with WebSocket support
- ✅ **DTMF Recognition** - Detect and process touch-tone inputs
- ✅ **Speech Recognition** - Convert speech to text (when configured)

### Call Recording
- ✅ **Start/Stop/Pause/Resume Recording** - Full recording control
- ✅ **Download Recordings** - Retrieve recorded audio files
- ✅ **Recording Metadata** - Access recording information and statistics

### Participant Management
- ✅ **Add Participants** - Add PSTN or ACS users to ongoing calls
- ✅ **Remove Participants** - Remove participants from calls
- ✅ **Hold/Unhold** - Put participants on hold with optional music
- ✅ **Mute Participants** - Mute specific participants
- ✅ **Transfer Calls** - Transfer calls between participants

### Real-time Features
- ✅ **Event Webhooks** - Handle Azure Communication Services events
- ✅ **WebSocket Streaming** - Real-time audio and transcription data
- ✅ **Live Logging** - Real-time log viewing in web interface

## Requirements

### System Requirements
- **Python 3.8+** (required)
- **Virtual Environment** (recommended)
- **Azure Communication Services Resource**
- **Public endpoint** (for webhooks)

### Azure Resources Needed
- Azure Communication Services resource with phone number
- Optional: Azure Cognitive Services for call intelligence
- Optional: Azure Storage for recording storage

## Quick Start

### 1. Automatic Setup (Recommended)
```bash
# Run the automated setup script
python start.py
```

This script will:
- Check Python version compatibility
- Create virtual environment
- Install all dependencies
- Create environment configuration file
- Start the application

### 2. Manual Setup

#### Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Configure Environment
```bash
# Copy environment template
cp .env.python.template .env

# Edit .env file with your configuration
```

#### Start Application
```bash
python main.py
```

## Configuration

### Environment Variables

Copy `.env.python.template` to `.env` and configure:

```bash
# Required Configuration
CONNECTION_STRING=your_acs_connection_string_here
ACS_RESOURCE_PHONE_NUMBER=+1234567890
CALLBACK_URI=https://your-server-domain.com

# Optional Configuration
PORT=3000
COGNITIVE_SERVICES_ENDPOINT=your_cognitive_services_endpoint
SSL_KEY_PATH=./certs/server.key
SSL_CERT_PATH=./certs/server.crt
```

### SSL/HTTPS Configuration

For production deployment, configure SSL certificates:

1. **PEM Format** (recommended):
   ```bash
   SSL_KEY_PATH=./certs/server.key
   SSL_CERT_PATH=./certs/server.crt
   ```

2. **PFX Format**:
   ```bash
   SSL_PFX_PATH=./certs/server.pfx
   SSL_PFX_PASSWORD=your_password
   ```

## API Endpoints

### Web Interface
- `GET /` - Main application dashboard

### Call Operations
- `GET /outboundCall?targetPhoneNumber={number}&isPstn=true` - Place PSTN call
- `GET /outboundCallACS?acsUserId={userId}` - Place ACS call
- `GET /terminateCallAsync?isForEveryone={boolean}` - Terminate call

### Media Operations
- `GET /playMediaToAllWithFileSource` - Play media to all participants
- `GET /startRecording?recordingContent=audio&recordingChannel=mixed&recordingFormat=wav` - Start recording
- `GET /download` - Download recording
- `GET /downloadMetadata` - Download recording metadata

### Webhook Endpoints
- `POST /api/incomingCall` - Handle incoming call events
- `POST /api/callbacks` - Handle call automation events
- `POST /api/recordingFileStatus` - Handle recording events

### Utility Endpoints
- `GET /api/logs` - Get recent application logs
- `GET /clearLogs` - Clear application logs
- `GET /audioprompt/{filename}` - Serve audio files

## Development

### Project Structure
```
├── main.py                     # Main Python application
├── requirements.txt           # Python dependencies
├── start.py                  # Automated setup script
├── .env.python.template      # Environment configuration template
├── src/
│   ├── resources/
│   │   └── media_prompts/    # Audio files for prompts
│   └── webpage/
│       └── index.html        # Web interface (if needed)
└── certs/                    # SSL certificates (optional)
```

### Key Differences from TypeScript Version

1. **Framework**: Uses Flask instead of Express.js
2. **Async Handling**: Uses Python's asyncio for asynchronous operations
3. **WebSockets**: Simplified WebSocket implementation (can be enhanced)
4. **Type Safety**: Uses Python type hints for better code clarity
5. **Error Handling**: Python-style exception handling
6. **Logging**: Enhanced logging with Python's logging module

### Adding New Features

1. **New API Endpoint**:
   ```python
   @app.route('/your-endpoint')
   async def your_function():
       # Your implementation
       return jsonify({'status': 'success'})
   ```

2. **New Event Handler**:
   ```python
   # Add to handle_callbacks function
   elif event_type == "Microsoft.Communication.YourEvent":
       logger.info("Received YourEvent")
       # Handle your event
   ```

## Deployment

### Local Development
```bash
python start.py
```

### Production Deployment

#### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:3000
```

#### Using Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 3000

CMD ["python", "main.py"]
```

#### Environment Variables for Production
```bash
FLASK_ENV=production
FLASK_DEBUG=False
LOG_LEVEL=WARNING
```

## Troubleshooting

### Common Issues

1. **Import Errors**:
   ```bash
   # Ensure virtual environment is activated
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Connection Errors**:
   - Verify CONNECTION_STRING is correct
   - Check if CALLBACK_URI is publicly accessible
   - Ensure phone number format includes country code

3. **SSL Errors**:
   - Verify certificate paths in .env file
   - Check certificate file permissions
   - Consider using HTTP for development

4. **Webhook Issues**:
   - Ensure CALLBACK_URI is publicly accessible
   - Check firewall and network security group settings
   - Verify webhook endpoints are responding with 200 status

### Logs and Debugging

- **View Logs**: Access `/api/logs` endpoint or check console output
- **Clear Logs**: Use `/clearLogs` endpoint
- **Debug Mode**: Set `FLASK_DEBUG=True` in .env for detailed error messages

## Migration from TypeScript

This Python application maintains feature parity with the original TypeScript version:

- ✅ All API endpoints preserved
- ✅ Same webhook event handling
- ✅ Identical functionality for call management
- ✅ Compatible with existing Azure configurations
- ✅ Same audio file and media handling

Simply update your environment configuration and the application will work with your existing Azure Communication Services setup.

## Support

For issues specific to this Python implementation, please check:

1. **Environment Configuration**: Ensure all required variables are set
2. **Dependencies**: Verify all packages are installed correctly
3. **Azure Setup**: Confirm your Azure Communication Services resource is configured
4. **Network Access**: Ensure your webhook endpoints are publicly accessible

For Azure Communication Services specific issues, refer to the [official documentation](https://docs.microsoft.com/en-us/azure/communication-services/).