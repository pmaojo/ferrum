import fs from 'fs/promises';
import path from 'path';
import { Readable } from 'node:stream';

import type { Request, Response } from 'express';
import express from 'express';
import multer from 'multer';
import { v4 as uuidv4 } from 'uuid';

import { logger } from '../utils/logger';
import {
  createPermaGraphStandardsClient,
  PermaGraphStandardsClientError,
} from '../services/permaGraphStandardsClient';

const router = express.Router();
const standardsClient = createPermaGraphStandardsClient();

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: async (req, file, cb) => {
    const uploadDir = path.join(process.cwd(), 'uploads', 'imports');
    await fs.mkdir(uploadDir, { recursive: true });
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueName = `${uuidv4()}-${file.originalname}`;
    cb(null, uniqueName);
  },
});

const upload = multer({
  storage,
  limits: {
    fileSize: 50 * 1024 * 1024, // 50MB limit
  },
  fileFilter: (req, file, cb) => {
    // Accept RDF-related file types
    const allowedTypes = [
      'text/turtle',
      'application/rdf+xml',
      'application/ld+json',
      'application/json',
      'application/xml',
      'text/plain',
      'application/n-triples',
    ];

    const allowedExtensions = [
      '.ttl',
      '.turtle',
      '.rdf',
      '.xml',
      '.jsonld',
      '.json',
      '.nt',
    ];
    const fileExtension = path.extname(file.originalname).toLowerCase();

    if (
      allowedTypes.includes(file.mimetype) ||
      allowedExtensions.includes(fileExtension)
    ) {
      cb(null, true);
    } else {
      cb(new Error(`Unsupported file type: ${file.mimetype}`));
    }
  },
});

interface ExportRequest {
  projectId: string;
  format: string;
  options: {
    includeMetadata?: boolean;
    includeValidation?: boolean;
    includeProvenance?: boolean;
    compressOutput?: boolean;
  };
}

interface ImportRequest {
  projectId: string;
  format: string;
  options: {
    mergeStrategy?: string;
    validateBefore?: boolean;
    validateAfter?: boolean;
    createBackup?: boolean;
    resolveConflicts?: boolean;
    dryRun?: boolean;
  };
  url?: string;
}

/**
 * @kthulu:extend - Standards export/import API routes
 * Handles RDF/Turtle, JSON-LD, SHACL, and other standard format operations
 */

// Export ontology in various formats
router.post('/export', async (req: Request, res: Response) => {
  try {
    const { projectId, format, options }: ExportRequest = req.body;

    if (!projectId || !format) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: projectId, format',
      });
    }

    logger.info(
      `🚀 Starting export for project ${projectId} in format ${format}`
    );

    const exportResponse = await standardsClient.exportOntology({
      projectId,
      format,
      options: options && typeof options === 'object' ? options : {},
    });

    if (!exportResponse.body) {
      res.status(exportResponse.status).end();
      return;
    }

    res.status(exportResponse.status);

    exportResponse.headers.forEach((value, key) => {
      if (key.toLowerCase() === 'transfer-encoding') {
        return;
      }
      res.setHeader(key, value);
    });

    const nodeStream = Readable.fromWeb(
      exportResponse.body as unknown as ReadableStream
    );
    nodeStream.on('error', (streamError) => {
      logger.error('❌ Failed to stream export payload from PermaGraph', {
        error: streamError,
      });
      res.destroy(streamError as Error);
    });
    nodeStream.pipe(res);
  } catch (error) {
    if (error instanceof PermaGraphStandardsClientError) {
      logger.error('❌ PermaGraph export error:', error);
      return respondWithPermaGraphError(res, error);
    }

    logger.error('❌ Export error:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown export error',
    });
  }
});

// Import ontology from file or URL
router.post(
  '/import',
  upload.single('file'),
  async (req: Request, res: Response) => {
    const uploadedFilePath = req.file?.path;
    try {
      const {
        projectId,
        format,
        options: optionsRaw,
        url,
      }: ImportRequest & { options?: string | Record<string, unknown> } =
        req.body;
      const { file } = req;

      if (!projectId || !format) {
        return res.status(400).json({
          success: false,
          error: 'Missing required fields: projectId, format',
        });
      }

      if (!file && !url) {
        return res.status(400).json({
          success: false,
          error: 'Either file or URL must be provided',
        });
      }

      let parsedOptions: Record<string, unknown> = {};
      if (typeof optionsRaw === 'string' && optionsRaw.trim().length > 0) {
        parsedOptions = JSON.parse(optionsRaw);
      } else if (
        optionsRaw &&
        typeof optionsRaw === 'object' &&
        !Array.isArray(optionsRaw)
      ) {
        parsedOptions = optionsRaw as Record<string, unknown>;
      }

      logger.info(
        `🚀 Starting import for project ${projectId} from ${file ? 'file' : 'URL'}`
      );

      let importResult: Record<string, unknown> | undefined;

      if (file) {
        importResult = await standardsClient.importOntologyFromFile({
          projectId,
          format,
          filePath: file.path,
          options: parsedOptions,
        });
      } else if (url) {
        importResult = await standardsClient.importOntologyFromUrl({
          projectId,
          format,
          url,
          options: parsedOptions,
        });
      }

      res.json({ success: true, ...(importResult ?? {}) });
    } catch (error) {
      if (error instanceof SyntaxError) {
        logger.error('❌ Invalid import options payload', error);
        return res.status(400).json({
          success: false,
          error: 'Invalid import options payload',
        });
      }

      if (error instanceof PermaGraphStandardsClientError) {
        logger.error('❌ PermaGraph import error:', error);
        return respondWithPermaGraphError(res, error);
      }

      logger.error('❌ Import error:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown import error',
      });
    } finally {
      if (uploadedFilePath) {
        try {
          await fs.unlink(uploadedFilePath);
        } catch (cleanupError) {
          logger.warn('⚠️ Could not clean up uploaded file:', cleanupError);
        }
      }
    }
  }
);

// Export SHACL validation shapes
router.post('/export/shapes', async (req: Request, res: Response) => {
  try {
    const { projectId } = req.body;

    if (!projectId) {
      return res.status(400).json({
        success: false,
        error: 'Missing required field: projectId',
      });
    }

    logger.info(`🔍 Exporting SHACL shapes for project ${projectId}`);

    const shapesResponse = await standardsClient.exportShapes({ projectId });

    if (!shapesResponse.body) {
      res.status(shapesResponse.status).end();
      return;
    }

    res.status(shapesResponse.status);
    shapesResponse.headers.forEach((value, key) => {
      if (key.toLowerCase() === 'transfer-encoding') {
        return;
      }
      res.setHeader(key, value);
    });

    const nodeStream = Readable.fromWeb(
      shapesResponse.body as unknown as ReadableStream
    );
    nodeStream.on('error', (streamError) => {
      logger.error('❌ Failed to stream SHACL shapes from PermaGraph', {
        error: streamError,
      });
      res.destroy(streamError as Error);
    });
    nodeStream.pipe(res);
  } catch (error) {
    if (error instanceof PermaGraphStandardsClientError) {
      logger.error('❌ PermaGraph SHACL export error:', error);
      return respondWithPermaGraphError(res, error);
    }

    logger.error('❌ SHACL shapes export error:', error);
    res.status(500).json({
      success: false,
      error:
        error instanceof Error ? error.message : 'Unknown shapes export error',
    });
  }
});

// Import SHACL validation shapes
router.post(
  '/import/shapes',
  upload.single('shapes'),
  async (req: Request, res: Response) => {
    try {
      const { projectId } = req.body;
      const shapesFile = req.file;

      if (!projectId || !shapesFile) {
        return res.status(400).json({
          success: false,
          error: 'Missing required fields: projectId, shapes file',
        });
      }

      logger.info(`🔍 Importing SHACL shapes for project ${projectId}`);

      const importResult = await callPermaGraphImportShapes({
        project_id: projectId,
        shapes_file_path: shapesFile.path,
      });

      // Clean up uploaded file
      try {
        await fs.unlink(shapesFile.path);
      } catch (cleanupError) {
        logger.warn('⚠️ Could not clean up shapes file:', cleanupError);
      }

      if (!importResult.success) {
        return res.status(500).json({
          success: false,
          error: importResult.error || 'SHACL shapes import failed',
        });
      }

      res.json({
        success: true,
        shapes_imported: importResult.shapes_count || 0,
        validation_passed: importResult.validation_passed !== false,
        validation_warnings: importResult.validation_warnings || [],
      });
    } catch (error) {
      logger.error('❌ SHACL shapes import error:', error);

      // Clean up uploaded file on error
      if (req.file) {
        try {
          await fs.unlink(req.file.path);
        } catch (cleanupError) {
          logger.warn(
            '⚠️ Could not clean up shapes file after error:',
            cleanupError
          );
        }
      }

      res.status(500).json({
        success: false,
        error:
          error instanceof Error
            ? error.message
            : 'Unknown shapes import error',
      });
    }
  }
);

// Export for visualization tools
router.post('/export/visualization', async (req: Request, res: Response) => {
  try {
    const { projectId, tool } = req.body;

    if (!projectId || !tool) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: projectId, tool',
      });
    }

    logger.info(`📊 Exporting for visualization tool: ${tool}`);

    const exportResult = await callPermaGraphExportVisualization({
      project_id: projectId,
      tool,
    });

    if (!exportResult.success) {
      return res.status(500).json({
        success: false,
        error: exportResult.error || 'Visualization export failed',
      });
    }

    res.json({
      success: true,
      content: exportResult.content,
      format: exportResult.format || tool,
      node_count: exportResult.node_count,
      link_count: exportResult.link_count,
      size_bytes: exportResult.size_bytes || 0,
    });
  } catch (error) {
    logger.error('❌ Visualization export error:', error);
    res.status(500).json({
      success: false,
      error:
        error instanceof Error
          ? error.message
          : 'Unknown visualization export error',
    });
  }
});

// Get supported formats
router.get('/formats', (req: Request, res: Response) => {
  res.json({
    export_formats: [
      {
        id: 'turtle',
        name: 'Turtle (TTL)',
        description: 'Terse RDF Triple Language',
        extension: 'ttl',
        mime_type: 'text/turtle',
      },
      {
        id: 'rdf-xml',
        name: 'RDF/XML',
        description: 'XML serialization of RDF',
        extension: 'rdf',
        mime_type: 'application/rdf+xml',
      },
      {
        id: 'json-ld',
        name: 'JSON-LD',
        description: 'JSON for Linked Data',
        extension: 'jsonld',
        mime_type: 'application/ld+json',
      },
      {
        id: 'n-triples',
        name: 'N-Triples',
        description: 'Simple line-based RDF format',
        extension: 'nt',
        mime_type: 'application/n-triples',
      },
      {
        id: 'shacl',
        name: 'SHACL Shapes',
        description: 'Validation shapes for RDF data',
        extension: 'ttl',
        mime_type: 'text/turtle',
      },
      {
        id: 'graphml',
        name: 'GraphML',
        description: 'Graph format for visualization tools',
        extension: 'graphml',
        mime_type: 'application/xml',
      },
    ],
    import_formats: [
      {
        id: 'turtle',
        name: 'Turtle (TTL)',
        description: 'Terse RDF Triple Language',
        extensions: ['.ttl', '.turtle'],
        mime_types: ['text/turtle'],
      },
      {
        id: 'rdf-xml',
        name: 'RDF/XML',
        description: 'XML serialization of RDF',
        extensions: ['.rdf', '.xml'],
        mime_types: ['application/rdf+xml', 'application/xml'],
      },
      {
        id: 'json-ld',
        name: 'JSON-LD',
        description: 'JSON for Linked Data',
        extensions: ['.jsonld', '.json'],
        mime_types: ['application/ld+json', 'application/json'],
      },
      {
        id: 'kthulu-json',
        name: 'Kthulu Project',
        description: 'Kthulu project export format',
        extensions: ['.json'],
        mime_types: ['application/json'],
      },
    ],
    visualization_tools: ['cytoscape', 'gephi', 'yfiles', 'neo4j', 'd3'],
  });
});

// Download exported file
router.get('/download/:fileId', async (req: Request, res: Response) => {
  try {
    const { fileId } = req.params;
    const downloadDir = path.join(process.cwd(), 'downloads');
    const filePath = path.join(downloadDir, fileId);

    // Check if file exists
    try {
      await fs.access(filePath);
    } catch {
      return res.status(404).json({
        success: false,
        error: 'File not found',
      });
    }

    // Get file stats
    const stats = await fs.stat(filePath);

    // Set appropriate headers
    res.setHeader('Content-Type', 'application/octet-stream');
    res.setHeader('Content-Disposition', `attachment; filename="${fileId}"`);
    res.setHeader('Content-Length', stats.size);

    // Stream file to response
    const fileStream = fs.createReadStream(filePath);
    fileStream.pipe(res);

    // Clean up file after download (optional)
    fileStream.on('end', async () => {
      try {
        // Wait a bit then delete the file
        setTimeout(async () => {
          try {
            await fs.unlink(filePath);
            logger.info(`🗑️ Cleaned up download file: ${fileId}`);
          } catch (cleanupError) {
            logger.warn('⚠️ Could not clean up download file:', cleanupError);
          }
        }, 5000); // 5 second delay
      } catch (error) {
        logger.warn('⚠️ Error scheduling file cleanup:', error);
      }
    });
  } catch (error) {
    logger.error('❌ Download error:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown download error',
    });
  }
});

function respondWithPermaGraphError(
  res: Response,
  error: PermaGraphStandardsClientError
): Response {
  const { details } = error;

  if (details && typeof details === 'object' && !Array.isArray(details)) {
    return res.status(error.statusCode).json({
      success: false,
      error: error.message,
      ...(details as Record<string, unknown>),
    });
  }

  return res.status(error.statusCode).json({
    success: false,
    error: error.message,
    details,
  });
}

async function callPermaGraphImportShapes(params: any): Promise<any> {
  // Mock implementation
  return {
    success: true,
    shapes_count: 5,
    validation_passed: true,
    validation_warnings: [],
  };
}

async function callPermaGraphExportVisualization(params: any): Promise<any> {
  // Mock implementation
  if (params.tool === 'd3') {
    return {
      success: true,
      content: JSON.stringify({
        nodes: [
          { id: 'module1', label: 'User Module', type: 'Module' },
          { id: 'usecase1', label: 'Create User', type: 'UseCase' },
        ],
        links: [{ source: 0, target: 1, relation: 'definesUseCase' }],
      }),
      format: 'json',
      node_count: 2,
      link_count: 1,
      size_bytes: 150,
    };
  }

  return {
    success: true,
    content: '<!-- GraphML content -->',
    format: 'graphml',
    node_count: 10,
    link_count: 15,
    size_bytes: 500,
  };
}

export default router;
