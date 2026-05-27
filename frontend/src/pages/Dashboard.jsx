import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Tile,
  Grid,
  Column,
  Loading,
  InlineNotification,
} from '@carbon/react';
import { Upload, Play, DocumentBlank } from '@carbon/icons-react';
import { checkMCPHealth } from '../services/api';
import './Dashboard.scss';

const Dashboard = () => {
  const navigate = useNavigate();
  const [mcpStatus, setMcpStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      setLoading(true);
      const response = await checkMCPHealth();
      setMcpStatus(response);
      setError(null);
    } catch (err) {
      setError('Failed to connect to backend services');
      console.error('Health check failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Migration Copilot Dashboard</h1>
        <p className="page-description">
          Enterprise application modernization powered by AI agents
        </p>
      </div>

      {error && (
        <InlineNotification
          kind="error"
          title="Connection Error"
          subtitle={error}
          onCloseButtonClick={() => setError(null)}
          style={{ marginBottom: '2rem' }}
        />
      )}

      {loading ? (
        <Loading description="Checking system status..." withOverlay={false} />
      ) : (
        <>
          <Grid className="dashboard-grid">
            <Column lg={4} md={4} sm={4}>
              <Tile className="dashboard-tile">
                <div className="tile-icon">
                  <Upload size={32} />
                </div>
                <h3>Upload Documents</h3>
                <p>
                  Upload application documentation, configuration files, and source code
                  for analysis.
                </p>
                <Button
                  kind="primary"
                  onClick={() => navigate('/upload')}
                  style={{ marginTop: '1rem' }}
                >
                  Upload Files
                </Button>
              </Tile>
            </Column>

            <Column lg={4} md={4} sm={4}>
              <Tile className="dashboard-tile">
                <div className="tile-icon">
                  <Play size={32} />
                </div>
                <h3>Start Workflow</h3>
                <p>
                  Execute the AI-powered migration analysis workflow to extract facts and
                  generate recommendations.
                </p>
                <Button
                  kind="secondary"
                  onClick={() => navigate('/workflow/test-project')}
                  style={{ marginTop: '1rem' }}
                >
                  Start Analysis
                </Button>
              </Tile>
            </Column>

            <Column lg={4} md={4} sm={4}>
              <Tile className="dashboard-tile">
                <div className="tile-icon">
                  <DocumentBlank size={32} />
                </div>
                <h3>View Results</h3>
                <p>
                  Review extracted facts, questionnaire gaps, and migration
                  recommendations.
                </p>
                <Button
                  kind="tertiary"
                  onClick={() => navigate('/facts/test-project')}
                  style={{ marginTop: '1rem' }}
                >
                  View Facts
                </Button>
              </Tile>
            </Column>
          </Grid>

          <div className="status-section">
            <h2>System Status</h2>
            <Grid>
              <Column lg={8} md={8} sm={4}>
                <Tile className="status-tile">
                  <div className="status-item">
                    <span className="status-label">Backend API:</span>
                    <span className={`status-value ${mcpStatus ? 'status-ok' : 'status-error'}`}>
                      {mcpStatus ? '✓ Connected' : '✗ Disconnected'}
                    </span>
                  </div>
                  <div className="status-item">
                    <span className="status-label">MCP Gateway:</span>
                    <span className={`status-value ${mcpStatus?.status === 'healthy' ? 'status-ok' : 'status-error'}`}>
                      {mcpStatus?.status === 'healthy' ? '✓ Healthy' : '✗ Unavailable'}
                    </span>
                  </div>
                  {mcpStatus?.gateway_url && (
                    <div className="status-item">
                      <span className="status-label">Gateway URL:</span>
                      <span className="status-value status-url">
                        {mcpStatus.gateway_url}
                      </span>
                    </div>
                  )}
                </Tile>
              </Column>
            </Grid>
          </div>
        </>
      )}
    </div>
  );
};

export default Dashboard;

// Made with Bob
