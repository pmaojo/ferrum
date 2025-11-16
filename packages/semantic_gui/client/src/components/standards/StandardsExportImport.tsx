import React, { useState, useCallback, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import {
  Download,
  Upload,
  FileText,
  Database,
  Share2,
  CheckCircle,
  AlertTriangle,
  Info,
  Copy,
  ExternalLink,
  Settings,
  Loader2,
  X,
  Eye,
  Code,
  Globe,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import useStandards from '@/hooks/useStandards';
import {
  ExportOptions,
  ImportOptionParams,
  ExportResponse,
  ImportResponse,
} from '@/services/standardsService';
import { formatDistanceToNow } from 'date-fns';

interface ExportFormat {
  id: string;
  name: string;
  description: string;
  extension: string;
  mimeType: string;
  icon: React.ReactNode;
}

interface ImportFormat {
  id: string;
  name: string;
  description: string;
  extensions: string[];
  mimeTypes: string[];
  icon: React.ReactNode;
}

interface ExportResult {
  success: boolean;
  format: string;
  size: number;
  tripleCount: number;
  downloadUrl?: string;
  content?: string;
  metadata?: any;
}

interface ImportResult {
  success: boolean;
  format: string;
  triplesImported: number;
  triplesUpdated: number;
  triplesRemoved: number;
  validationPassed: boolean;
  warnings: string[];
  errors: string[];
}

interface StandardsExportImportProps {
  projectId: string;
  className?: string;
}

/**
 * @kthulu:extend - Standards export/import interface for Kthulu-PermaGraph integration
 * Handles RDF/Turtle, JSON-LD, SHACL, and other standard format operations
 */
export function StandardsExportImport({
  projectId,
  className,
}: StandardsExportImportProps) {
  const { toast } = useToast();
  const { exportStandards, importStandards } = useStandards();
  const [activeTab, setActiveTab] = useState('export');
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [importProgress, setImportProgress] = useState(0);

  const [formatSource, setFormatSource] = useState<'permagraph' | 'standards'>(
    'permagraph'
  );

  // Export state
  const [selectedExportFormat, setSelectedExportFormat] = useState('turtle');
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    includeMetadata: true,
    includeValidation: true,
    includeProvenance: true,
    compressOutput: false,
  });
  const [exportResult, setExportResult] = useState<ExportResult | null>(null);

  // Import state
  const [selectedImportFormat, setSelectedImportFormat] = useState('turtle');
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importUrl, setImportUrl] = useState('');
  const [importOptions, setImportOptions] = useState<ImportOptionParams>({
    mergeStrategy: 'replace',
    validateBefore: true,
    validateAfter: true,
    createBackup: true,
    resolveConflicts: true,
    dryRun: false,
  });
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  const allExportFormats: ExportFormat[] = [
    {
      id: 'turtle',
      name: 'Turtle (TTL)',
      description: 'Terse RDF Triple Language - human-readable RDF format',
      extension: 'ttl',
      mimeType: 'text/turtle',
      icon: <FileText className="h-4 w-4" />,
    },
    {
      id: 'rdf-xml',
      name: 'RDF/XML',
      description: 'XML serialization of RDF - standard W3C format',
      extension: 'rdf',
      mimeType: 'application/rdf+xml',
      icon: <Code className="h-4 w-4" />,
    },
    {
      id: 'json-ld',
      name: 'JSON-LD',
      description: 'JSON for Linked Data - web-friendly RDF format',
      extension: 'jsonld',
      mimeType: 'application/ld+json',
      icon: <Database className="h-4 w-4" />,
    },
    {
      id: 'n-triples',
      name: 'N-Triples',
      description: 'Simple line-based RDF format',
      extension: 'nt',
      mimeType: 'application/n-triples',
      icon: <FileText className="h-4 w-4" />,
    },
    {
      id: 'shacl',
      name: 'SHACL Shapes',
      description: 'Validation shapes for RDF data',
      extension: 'ttl',
      mimeType: 'text/turtle',
      icon: <CheckCircle className="h-4 w-4" />,
    },
    {
      id: 'graphml',
      name: 'GraphML',
      description: 'Graph format for visualization tools',
      extension: 'graphml',
      mimeType: 'application/xml',
      icon: <Share2 className="h-4 w-4" />,
    },
  ];

  const allImportFormats: ImportFormat[] = [
    {
      id: 'turtle',
      name: 'Turtle (TTL)',
      description: 'Terse RDF Triple Language',
      extensions: ['.ttl', '.turtle'],
      mimeTypes: ['text/turtle'],
      icon: <FileText className="h-4 w-4" />,
    },
    {
      id: 'rdf-xml',
      name: 'RDF/XML',
      description: 'XML serialization of RDF',
      extensions: ['.rdf', '.xml'],
      mimeTypes: ['application/rdf+xml', 'application/xml'],
      icon: <Code className="h-4 w-4" />,
    },
    {
      id: 'json-ld',
      name: 'JSON-LD',
      description: 'JSON for Linked Data',
      extensions: ['.jsonld', '.json'],
      mimeTypes: ['application/ld+json', 'application/json'],
      icon: <Database className="h-4 w-4" />,
    },
    {
      id: 'kthulu-json',
      name: 'Kthulu Project',
      description: 'Kthulu project export format',
      extensions: ['.json'],
      mimeTypes: ['application/json'],
      icon: <Share2 className="h-4 w-4" />,
    },
  ];

  const exportFormats = allExportFormats;
  const importFormats =
    formatSource === 'standards'
      ? allImportFormats.filter((f) => f.id !== 'kthulu-json')
      : allImportFormats;

  useEffect(() => {
    if (!exportFormats.find((f) => f.id === selectedExportFormat)) {
      setSelectedExportFormat(exportFormats[0]?.id || '');
    }
    if (!importFormats.find((f) => f.id === selectedImportFormat)) {
      setSelectedImportFormat(importFormats[0]?.id || '');
    }
  }, [formatSource]);

  const handleExport = useCallback(async () => {
    if (!selectedExportFormat) return;

    setIsExporting(true);
    setExportProgress(0);
    setExportResult(null);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setExportProgress((prev) => Math.min(prev + 10, 90));
      }, 200);

      let result: ExportResponse;
      if (formatSource === 'standards') {
        result = await exportStandards(
          projectId,
          selectedExportFormat,
          exportOptions,
        );
      } else {
        const response = await fetch('/api/v1/export', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            projectId,
            format: selectedExportFormat,
            options: exportOptions,
          }),
        });
        if (!response.ok) {
          throw new Error(`Export failed: ${response.statusText}`);
        }
        result = (await response.json()) as ExportResponse;
      }

      clearInterval(progressInterval);
      setExportProgress(100);

      if (result.success) {
        setExportResult({
          success: true,
          format: selectedExportFormat,
          size: result.size_bytes || 0,
          tripleCount: result.metadata?.triple_count || 0,
          downloadUrl: result.download_url,
          content: result.content,
          metadata: result.metadata,
        });

        toast({
          title: 'Export Completed',
          description: `Successfully exported ${
            result.metadata?.triple_count || 0
          } triples`,
        });
      } else {
        throw new Error(result.error || 'Export failed');
      }
    } catch (error) {
      console.error('Export error:', error);
      toast({
        title: 'Export Failed',
        description:
          error instanceof Error ? error.message : 'Unknown error occurred',
        variant: 'destructive',
      });
      setExportResult({
        success: false,
        format: selectedExportFormat,
        size: 0,
        tripleCount: 0,
      });
    } finally {
      setIsExporting(false);
    }
  }, [
    selectedExportFormat,
    exportOptions,
    projectId,
    formatSource,
    exportStandards,
    toast,
  ]);

  const handleImport = useCallback(async () => {
    if (!importFile && !importUrl) {
      toast({
        title: 'No Source Selected',
        description: 'Please select a file or enter a URL to import',
        variant: 'destructive',
      });
      return;
    }

    setIsImporting(true);
    setImportProgress(0);
    setImportResult(null);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setImportProgress((prev) => Math.min(prev + 10, 90));
      }, 200);

      let result: ImportResponse;
      if (formatSource === 'standards') {
        result = await importStandards(
          projectId,
          selectedImportFormat,
          importFile ?? undefined,
          importUrl || undefined,
          importOptions,
        );
      } else {
        const formData = new FormData();
        formData.append('projectId', projectId);
        formData.append('format', selectedImportFormat);
        formData.append('options', JSON.stringify(importOptions));

        if (importFile) {
          formData.append('file', importFile);
        } else if (importUrl) {
          formData.append('url', importUrl);
        }

        const response = await fetch('/api/v1/import', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Import failed: ${response.statusText}`);
        }
        result = (await response.json()) as ImportResponse;
      }

      clearInterval(progressInterval);
      setImportProgress(100);

      if (result.success) {
        setImportResult({
          success: true,
          format: selectedImportFormat,
          triplesImported: result.triples_imported || 0,
          triplesUpdated: result.triples_updated || 0,
          triplesRemoved: result.triples_removed || 0,
          validationPassed: result.validation_passed !== false,
          warnings: result.validation_warnings || [],
          errors: [],
        });

        toast({
          title: 'Import Completed',
          description: `Successfully imported ${
            result.triples_imported || 0
          } triples`,
        });
      } else {
        setImportResult({
          success: false,
          format: selectedImportFormat,
          triplesImported: 0,
          triplesUpdated: 0,
          triplesRemoved: 0,
          validationPassed: false,
          warnings: [],
          errors: result.errors || ['Import failed'],
        });

        throw new Error(result.errors?.[0] || 'Import failed');
      }
    } catch (error) {
      console.error('Import error:', error);
      toast({
        title: 'Import Failed',
        description:
          error instanceof Error ? error.message : 'Unknown error occurred',
        variant: 'destructive',
      });
    } finally {
      setIsImporting(false);
    }
  }, [
    importFile,
    importUrl,
    selectedImportFormat,
    importOptions,
    projectId,
    formatSource,
    importStandards,
    toast,
  ]);

  const handleFileSelect = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file) {
        setImportFile(file);
        setImportUrl(''); // Clear URL if file is selected

        // Auto-detect format based on file extension
        const extension = '.' + file.name.split('.').pop()?.toLowerCase();
        const detectedFormat = importFormats.find((format) =>
          format.extensions.includes(extension)
        );
        if (detectedFormat) {
          setSelectedImportFormat(detectedFormat.id);
        }
      }
    },
    [importFormats]
  );

  const copyToClipboard = useCallback(
    (text: string) => {
      navigator.clipboard.writeText(text).then(() => {
        toast({
          title: 'Copied to Clipboard',
          description: 'Content has been copied to your clipboard',
        });
      });
    },
    [toast]
  );

  const downloadContent = useCallback((content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, []);

  return (
    <div className={`space-y-6 ${className}`}>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Share2 className="h-5 w-5" />
            <span>Standards Export/Import</span>
          </CardTitle>
          <CardDescription>
            Export and import ontologies in standard formats (RDF/Turtle,
            JSON-LD, SHACL)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4 space-y-2">
            <Label htmlFor="format-source">Format Type</Label>
            <Select
              value={formatSource}
              onValueChange={(value) =>
                setFormatSource(value as 'permagraph' | 'standards')
              }
            >
              <SelectTrigger id="format-source">
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="permagraph">PermaGraph</SelectItem>
                <SelectItem value="standards">Standards</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger
                value="export"
                className="flex items-center space-x-2"
              >
                <Download className="h-4 w-4" />
                <span>Export</span>
              </TabsTrigger>
              <TabsTrigger
                value="import"
                className="flex items-center space-x-2"
              >
                <Upload className="h-4 w-4" />
                <span>Import</span>
              </TabsTrigger>
            </TabsList>

            {/* Export Tab */}
            <TabsContent value="export" className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Export Configuration */}
                <div className="space-y-4">
                  <h3 className="text-lg font-medium">Export Configuration</h3>

                  <div className="space-y-3">
                    <div>
                      <Label htmlFor="export-format">Output Format</Label>
                      <Select
                        value={selectedExportFormat}
                        onValueChange={setSelectedExportFormat}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select format" />
                        </SelectTrigger>
                        <SelectContent>
                          {exportFormats.map((format) => (
                            <SelectItem key={format.id} value={format.id}>
                              <div className="flex items-center space-x-2">
                                {format.icon}
                                <div>
                                  <div className="font-medium">
                                    {format.name}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {format.description}
                                  </div>
                                </div>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <Separator />

                    <div className="space-y-3">
                      <h4 className="font-medium">Export Options</h4>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label htmlFor="include-metadata" className="text-sm">
                            Include Metadata
                          </Label>
                          <Switch
                            id="include-metadata"
                            checked={exportOptions.includeMetadata}
                            onCheckedChange={(checked) =>
                              setExportOptions((prev) => ({
                                ...prev,
                                includeMetadata: checked,
                              }))
                            }
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <Label
                            htmlFor="include-validation"
                            className="text-sm"
                          >
                            Include Validation Info
                          </Label>
                          <Switch
                            id="include-validation"
                            checked={exportOptions.includeValidation}
                            onCheckedChange={(checked) =>
                              setExportOptions((prev) => ({
                                ...prev,
                                includeValidation: checked,
                              }))
                            }
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <Label
                            htmlFor="include-provenance"
                            className="text-sm"
                          >
                            Include Provenance
                          </Label>
                          <Switch
                            id="include-provenance"
                            checked={exportOptions.includeProvenance}
                            onCheckedChange={(checked) =>
                              setExportOptions((prev) => ({
                                ...prev,
                                includeProvenance: checked,
                              }))
                            }
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <Label htmlFor="compress-output" className="text-sm">
                            Compress Output
                          </Label>
                          <Switch
                            id="compress-output"
                            checked={exportOptions.compressOutput}
                            onCheckedChange={(checked) =>
                              setExportOptions((prev) => ({
                                ...prev,
                                compressOutput: checked,
                              }))
                            }
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <Button
                    onClick={handleExport}
                    disabled={isExporting || !selectedExportFormat}
                    className="w-full"
                  >
                    {isExporting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Exporting...
                      </>
                    ) : (
                      <>
                        <Download className="h-4 w-4 mr-2" />
                        Export Ontology
                      </>
                    )}
                  </Button>

                  {isExporting && (
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Export Progress</span>
                        <span>{exportProgress}%</span>
                      </div>
                      <Progress value={exportProgress} />
                    </div>
                  )}
                </div>

                {/* Export Results */}
                <div className="space-y-4">
                  <h3 className="text-lg font-medium">Export Results</h3>

                  {exportResult ? (
                    <Card
                      className={
                        exportResult.success
                          ? 'border-green-200 bg-green-50'
                          : 'border-red-200 bg-red-50'
                      }
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center space-x-2 mb-3">
                          {exportResult.success ? (
                            <CheckCircle className="h-5 w-5 text-green-600" />
                          ) : (
                            <AlertTriangle className="h-5 w-5 text-red-600" />
                          )}
                          <span className="font-medium">
                            {exportResult.success
                              ? 'Export Successful'
                              : 'Export Failed'}
                          </span>
                        </div>

                        {exportResult.success && (
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span>Format:</span>
                              <Badge variant="outline">
                                {exportResult.format}
                              </Badge>
                            </div>
                            <div className="flex justify-between">
                              <span>Triples:</span>
                              <span className="font-medium">
                                {exportResult.tripleCount.toLocaleString()}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Size:</span>
                              <span className="font-medium">
                                {(exportResult.size / 1024).toFixed(1)} KB
                              </span>
                            </div>

                            {exportResult.content && (
                              <div className="mt-4 space-y-2">
                                <div className="flex space-x-2">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() =>
                                      copyToClipboard(exportResult.content!)
                                    }
                                  >
                                    <Copy className="h-4 w-4 mr-1" />
                                    Copy
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => {
                                      const format = exportFormats.find(
                                        (f) => f.id === exportResult.format
                                      );
                                      const filename = `${projectId}_ontology.${format?.extension || 'txt'}`;
                                      downloadContent(
                                        exportResult.content!,
                                        filename
                                      );
                                    }}
                                  >
                                    <Download className="h-4 w-4 mr-1" />
                                    Download
                                  </Button>
                                </div>

                                <ScrollArea className="h-32 border rounded p-2 bg-white">
                                  <pre className="text-xs">
                                    {exportResult.content.substring(0, 500)}...
                                  </pre>
                                </ScrollArea>
                              </div>
                            )}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Export results will appear here</p>
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>

            {/* Import Tab */}
            <TabsContent value="import" className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Import Configuration */}
                <div className="space-y-4">
                  <h3 className="text-lg font-medium">Import Configuration</h3>

                  <div className="space-y-3">
                    <div>
                      <Label htmlFor="import-format">Input Format</Label>
                      <Select
                        value={selectedImportFormat}
                        onValueChange={setSelectedImportFormat}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select format" />
                        </SelectTrigger>
                        <SelectContent>
                          {importFormats.map((format) => (
                            <SelectItem key={format.id} value={format.id}>
                              <div className="flex items-center space-x-2">
                                {format.icon}
                                <div>
                                  <div className="font-medium">
                                    {format.name}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {format.description}
                                  </div>
                                </div>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <Separator />

                    <div className="space-y-3">
                      <h4 className="font-medium">Import Source</h4>

                      <div>
                        <Label htmlFor="import-file">Upload File</Label>
                        <Input
                          id="import-file"
                          type="file"
                          onChange={handleFileSelect}
                          accept={importFormats
                            .find((f) => f.id === selectedImportFormat)
                            ?.extensions.join(',')}
                        />
                        {importFile && (
                          <div className="mt-2 text-sm text-gray-600">
                            Selected: {importFile.name} (
                            {(importFile.size / 1024).toFixed(1)} KB)
                          </div>
                        )}
                      </div>

                      <div className="text-center text-sm text-gray-500">
                        or
                      </div>

                      <div>
                        <Label htmlFor="import-url">Import from URL</Label>
                        <div className="flex space-x-2">
                          <Input
                            id="import-url"
                            placeholder="https://example.com/ontology.ttl"
                            value={importUrl}
                            onChange={(e) => {
                              setImportUrl(e.target.value);
                              if (e.target.value) setImportFile(null); // Clear file if URL is entered
                            }}
                          />
                          <Button variant="outline" size="sm">
                            <Globe className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>

                    <Separator />

                    <div className="space-y-3">
                      <h4 className="font-medium">Import Options</h4>

                      <div>
                        <Label htmlFor="merge-strategy">Merge Strategy</Label>
                        <Select
                          value={importOptions.mergeStrategy}
                          onValueChange={(value) =>
                            setImportOptions((prev) => ({
                              ...prev,
                              mergeStrategy: value,
                            }))
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="replace">
                              Replace - Replace entire ontology
                            </SelectItem>
                            <SelectItem value="merge">
                              Merge - Combine with existing
                            </SelectItem>
                            <SelectItem value="append">
                              Append - Add to existing
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label htmlFor="validate-before" className="text-sm">
                            Validate Before Import
                          </Label>
                          <Switch
                            id="validate-before"
                            checked={importOptions.validateBefore}
                            onCheckedChange={(checked) =>
                              setImportOptions((prev) => ({
                                ...prev,
                                validateBefore: checked,
                              }))
                            }
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <Label htmlFor="validate-after" className="text-sm">
                            Validate After Import
                          </Label>
                          <Switch
                            id="validate-after"
                            checked={importOptions.validateAfter}
                            onCheckedChange={(checked) =>
                              setImportOptions((prev) => ({
                                ...prev,
                                validateAfter: checked,
                              }))
                            }
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <Label htmlFor="create-backup" className="text-sm">
                            Create Backup
                          </Label>
                          <Switch
                            id="create-backup"
                            checked={importOptions.createBackup}
                            onCheckedChange={(checked) =>
                              setImportOptions((prev) => ({
                                ...prev,
                                createBackup: checked,
                              }))
                            }
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <Label htmlFor="dry-run" className="text-sm">
                            Dry Run (Preview Only)
                          </Label>
                          <Switch
                            id="dry-run"
                            checked={importOptions.dryRun}
                            onCheckedChange={(checked) =>
                              setImportOptions((prev) => ({
                                ...prev,
                                dryRun: checked,
                              }))
                            }
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <Button
                    onClick={handleImport}
                    disabled={isImporting || (!importFile && !importUrl)}
                    className="w-full"
                  >
                    {isImporting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Importing...
                      </>
                    ) : (
                      <>
                        <Upload className="h-4 w-4 mr-2" />
                        {importOptions.dryRun
                          ? 'Preview Import'
                          : 'Import Ontology'}
                      </>
                    )}
                  </Button>

                  {isImporting && (
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Import Progress</span>
                        <span>{importProgress}%</span>
                      </div>
                      <Progress value={importProgress} />
                    </div>
                  )}
                </div>

                {/* Import Results */}
                <div className="space-y-4">
                  <h3 className="text-lg font-medium">Import Results</h3>

                  {importResult ? (
                    <Card
                      className={
                        importResult.success
                          ? 'border-green-200 bg-green-50'
                          : 'border-red-200 bg-red-50'
                      }
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center space-x-2 mb-3">
                          {importResult.success ? (
                            <CheckCircle className="h-5 w-5 text-green-600" />
                          ) : (
                            <AlertTriangle className="h-5 w-5 text-red-600" />
                          )}
                          <span className="font-medium">
                            {importResult.success
                              ? 'Import Successful'
                              : 'Import Failed'}
                          </span>
                        </div>

                        {importResult.success && (
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span>Format:</span>
                              <Badge variant="outline">
                                {importResult.format}
                              </Badge>
                            </div>
                            <div className="flex justify-between">
                              <span>Triples Imported:</span>
                              <span className="font-medium text-green-600">
                                +{importResult.triplesImported.toLocaleString()}
                              </span>
                            </div>
                            {importResult.triplesUpdated > 0 && (
                              <div className="flex justify-between">
                                <span>Triples Updated:</span>
                                <span className="font-medium text-blue-600">
                                  ~
                                  {importResult.triplesUpdated.toLocaleString()}
                                </span>
                              </div>
                            )}
                            {importResult.triplesRemoved > 0 && (
                              <div className="flex justify-between">
                                <span>Triples Removed:</span>
                                <span className="font-medium text-red-600">
                                  -
                                  {importResult.triplesRemoved.toLocaleString()}
                                </span>
                              </div>
                            )}
                            <div className="flex justify-between">
                              <span>Validation:</span>
                              <Badge
                                variant={
                                  importResult.validationPassed
                                    ? 'default'
                                    : 'destructive'
                                }
                              >
                                {importResult.validationPassed
                                  ? 'Passed'
                                  : 'Failed'}
                              </Badge>
                            </div>
                          </div>
                        )}

                        {/* Warnings */}
                        {importResult.warnings.length > 0 && (
                          <div className="mt-4">
                            <h5 className="font-medium text-yellow-700 mb-2">
                              Warnings:
                            </h5>
                            <ul className="text-sm space-y-1">
                              {importResult.warnings.map((warning, index) => (
                                <li
                                  key={index}
                                  className="flex items-start space-x-2"
                                >
                                  <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                                  <span>{warning}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Errors */}
                        {importResult.errors.length > 0 && (
                          <div className="mt-4">
                            <h5 className="font-medium text-red-700 mb-2">
                              Errors:
                            </h5>
                            <ul className="text-sm space-y-1">
                              {importResult.errors.map((error, index) => (
                                <li
                                  key={index}
                                  className="flex items-start space-x-2"
                                >
                                  <X className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                                  <span>{error}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <Upload className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Import results will appear here</p>
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
