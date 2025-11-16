import { useState, useCallback } from 'react';
import {
  standardsService,
  ExportOptions,
  ExportResponse,
  ImportResponse,
  ImportOptionParams,
} from '@/services/standardsService';

export function useStandards() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const exportStandards = useCallback(
    async (
      projectId: string,
      format: string,
      options?: ExportOptions,
    ): Promise<ExportResponse> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await standardsService.exportStandards(
          projectId,
          format,
          options || {},
        );

        // Handle file download if URL or content provided
        if (result?.download_url) {
          const link = document.createElement('a');
          link.href = result.download_url;
          link.download = `export.${format}`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        } else if (result?.content) {
          const blob = new Blob([result.content], {
            type: result.mimeType || 'text/plain',
          });
          const url = window.URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = `export.${format}`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);
        }

        return result;
      } catch (e: any) {
        setError(e.message);
        throw e;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const importStandards = useCallback(
    async (
      projectId: string,
      format: string,
      file?: File,
      url?: string,
      options?: ImportOptionParams,
    ): Promise<ImportResponse> => {
      setIsLoading(true);
      setError(null);
      try {
        return await standardsService.importStandards(projectId, format, {
          file,
          url,
          options,
        });
      } catch (e: any) {
        setError(e.message);
        throw e;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  return { exportStandards, importStandards, isLoading, error };
}

export default useStandards;
