import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  FileUploader,
  TextInput,
  Button,
  InlineNotification,
  Loading,
  Tile,
  ProgressBar,
} from '@carbon/react';
import { CheckmarkFilled, ErrorFilled } from '@carbon/icons-react';
import { uploadDocument } from '../services/api';
import ProjectSelector from '../components/ProjectSelector';
import './DocumentUpload.scss';

const DocumentUpload = () => {
  const [searchParams] = useSearchParams();
  const [projectId, setProjectId] = useState('');
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Get project from URL params or localStorage
    const projectFromUrl = searchParams.get('project');
    const lastProject = localStorage.getItem('lastSelectedProject');
    const initialProject = projectFromUrl || lastProject || '';
    setProjectId(initialProject);
  }, [searchParams]);

  const handleProjectChange = (newProjectId) => {
    setProjectId(newProjectId);
    localStorage.setItem('lastSelectedProject', newProjectId);
  };

  const handleFileChange = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    setFiles(selectedFiles);
    setError(null);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one file to upload');
      return;
    }

    if (!projectId.trim()) {
      setError('Please enter a project ID');
      return;
    }

    setUploading(true);
    setError(null);
    const results = [];

    for (const file of files) {
      try {
        const result = await uploadDocument(file, projectId);
        results.push({
          filename: file.name,
          success: true,
          message: `Uploaded successfully (${result.chunks_created} chunks created)`,
          data: result,
        });
      } catch (err) {
        results.push({
          filename: file.name,
          success: false,
          message: err.response?.data?.detail || err.message || 'Upload failed',
        });
      }
    }

    setUploadResults(results);
    setUploading(false);
    setFiles([]);
  };

  const clearResults = () => {
    setUploadResults([]);
    setError(null);
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Upload Documents</h1>
        <p className="page-description">
          Upload application documentation, configuration files, and source code for
          analysis. Supported formats: PDF, DOCX, TXT, MD, XML, Properties, Excel.
        </p>
      </div>

      {error && (
        <InlineNotification
          kind="error"
          title="Upload Error"
          subtitle={error}
          onCloseButtonClick={() => setError(null)}
          style={{ marginBottom: '2rem' }}
        />
      )}

      <Tile className="upload-tile">
        <div className="upload-form">
          <div style={{ marginBottom: '1.5rem' }}>
            <ProjectSelector
              value={projectId}
              onChange={handleProjectChange}
              label="Select Project"
              disabled={uploading}
            />
          </div>

          <FileUploader
            labelTitle="Select files"
            labelDescription="Maximum file size is 50MB. You can select multiple files."
            buttonLabel="Choose files"
            filenameStatus="edit"
            accept={[
              '.pdf',
              '.docx',
              '.txt',
              '.md',
              '.xml',
              '.properties',
              '.xlsx',
              '.xls',
              '.csv',
            ]}
            multiple
            disabled={uploading}
            onChange={handleFileChange}
            size="md"
          />

          {files.length > 0 && (
            <div className="selected-files">
              <h4>Selected Files ({files.length})</h4>
              <ul>
                {files.map((file, index) => (
                  <li key={index}>
                    {file.name} ({(file.size / 1024).toFixed(2)} KB)
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="upload-actions">
            <Button
              kind="primary"
              onClick={handleUpload}
              disabled={uploading || files.length === 0 || !projectId.trim()}
            >
              {uploading ? 'Uploading...' : 'Upload Files'}
            </Button>
            {uploadResults.length > 0 && (
              <Button kind="secondary" onClick={clearResults}>
                Clear Results
              </Button>
            )}
          </div>
        </div>
      </Tile>

      {uploading && (
        <div className="upload-progress">
          <Loading description="Uploading and processing files..." withOverlay={false} />
          <ProgressBar
            label="Processing files"
            helperText="Parsing, chunking, and embedding documents..."
          />
        </div>
      )}

      {uploadResults.length > 0 && (
        <div className="upload-results">
          <h2>Upload Results</h2>
          {uploadResults.map((result, index) => (
            <Tile key={index} className={`result-tile ${result.success ? 'success' : 'error'}`}>
              <div className="result-header">
                {result.success ? (
                  <CheckmarkFilled size={24} className="result-icon success-icon" />
                ) : (
                  <ErrorFilled size={24} className="result-icon error-icon" />
                )}
                <span className="result-filename">{result.filename}</span>
              </div>
              <p className="result-message">{result.message}</p>
              {result.success && result.data && (
                <div className="result-details">
                  <div className="detail-item">
                    <span className="detail-label">Document ID:</span>
                    <span className="detail-value">{result.data.document_id}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Parser:</span>
                    <span className="detail-value">{result.data.parser_used}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Chunks:</span>
                    <span className="detail-value">{result.data.chunks_created}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Stored in:</span>
                    <span className="detail-value">{result.data.stored_in}</span>
                  </div>
                </div>
              )}
            </Tile>
          ))}
        </div>
      )}
    </div>
  );
};

export default DocumentUpload;

// Made with Bob
