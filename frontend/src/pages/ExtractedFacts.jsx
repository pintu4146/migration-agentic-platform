import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Tile,
  Loading,
  InlineNotification,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  DataTable,
  Table,
  TableHead,
  TableRow,
  TableHeader,
  TableBody,
  TableCell,
} from '@carbon/react';
import { getWorkflowState } from '../services/api';
import './ExtractedFacts.scss';

const ExtractedFacts = () => {
  const { projectId } = useParams();
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadState();
  }, [projectId]);

  const loadState = async () => {
    try {
      setLoading(true);
      const response = await getWorkflowState(projectId);
      setState(response);
      setError(null);
    } catch (err) {
      setError('Failed to load workflow state');
    } finally {
      setLoading(false);
    }
  };

  const renderFactsTable = (facts, category) => {
    if (!facts || facts.length === 0) {
      return <p className="empty-message">No {category} facts extracted yet.</p>;
    }

    const headers = [
      { key: 'name', header: 'Name' },
      { key: 'value', header: 'Value' },
      { key: 'confidence', header: 'Confidence' },
      { key: 'source', header: 'Source' },
    ];

    const rows = facts.map((fact, index) => ({
      id: `${category}-${index}`,
      name: fact.category || fact.name || fact.key || 'N/A',
      value: fact.fact || fact.evidence || (typeof fact.value === 'object' ? JSON.stringify(fact.value) : fact.value) || 'N/A',
      confidence: fact.confidence ? `${(fact.confidence * 100).toFixed(0)}%` : 'N/A',
      source: fact.source_id || fact.evidence_id || 'N/A',
    }));

    return (
      <DataTable rows={rows} headers={headers}>
        {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
          <Table {...getTableProps()}>
            <TableHead>
              <TableRow>
                {headers.map((header) => (
                  <TableHeader {...getHeaderProps({ header })} key={header.key}>
                    {header.header}
                  </TableHeader>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow {...getRowProps({ row })} key={row.id}>
                  {row.cells.map((cell) => (
                    <TableCell key={cell.id}>{cell.value}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DataTable>
    );
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Extracted Facts</h1>
        <p className="page-description">
          Project: <strong>{projectId}</strong>
        </p>
      </div>

      {error && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
          onCloseButtonClick={() => setError(null)}
          style={{ marginBottom: '2rem' }}
        />
      )}

      {loading ? (
        <Loading description="Loading extracted facts..." withOverlay={false} />
      ) : !state || !state.extracted_facts ? (
        <Tile>
          <div className="empty-state">
            <h3>No facts extracted yet</h3>
            <p>Run the workflow to extract facts from your documents.</p>
          </div>
        </Tile>
      ) : (
        <Tile className="facts-tile">
          <Tabs>
            <TabList aria-label="Extracted facts categories">
              <Tab>Technical Stack</Tab>
              <Tab>Dependencies</Tab>
              <Tab>Runtime Config</Tab>
              <Tab>Deployment</Tab>
              <Tab>Architecture</Tab>
              <Tab>Security</Tab>
              <Tab>Risks</Tab>
            </TabList>
            <TabPanels>
              <TabPanel>
                {renderFactsTable(
                  state.extracted_facts.technical_stack,
                  'technical_stack'
                )}
              </TabPanel>
              <TabPanel>
                {renderFactsTable(
                  state.extracted_facts.dependencies,
                  'dependencies'
                )}
              </TabPanel>
              <TabPanel>
                {renderFactsTable(
                  state.extracted_facts.runtime_config,
                  'runtime_config'
                )}
              </TabPanel>
              <TabPanel>
                {renderFactsTable(
                  state.extracted_facts.deployment_strategy,
                  'deployment_strategy'
                )}
              </TabPanel>
              <TabPanel>
                {renderFactsTable(
                  state.extracted_facts.architectural_decisions,
                  'architectural_decisions'
                )}
              </TabPanel>
              <TabPanel>
                {renderFactsTable(
                  state.extracted_facts.security_compliance,
                  'security_compliance'
                )}
              </TabPanel>
              <TabPanel>
                {renderFactsTable(state.extracted_facts.risks, 'risks')}
              </TabPanel>
            </TabPanels>
          </Tabs>
        </Tile>
      )}
    </div>
  );
};

export default ExtractedFacts;

// Made with Bob
