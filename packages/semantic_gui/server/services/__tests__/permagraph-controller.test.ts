import axios from 'axios';

import { PermaGraphController } from '../permagraph-controller';

jest.mock('axios');

const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('PermaGraphController external integrations', () => {
  let controller: PermaGraphController;

  beforeEach(() => {
    jest.resetAllMocks();
    controller = new PermaGraphController('test-project');
  });

  it('initializes explanation agent with PermaGraph provider', () => {
    const agent = controller.getAgent('explanation-agent');
    expect(agent?.config.llmProvider).toBe('permagraph');
  });

  describe('executeSemanticNavigation', () => {
    it('returns service data when call succeeds', async () => {
      mockedAxios.post.mockResolvedValue({ data: { search_results: ['a'] } });
      const result = await controller.executeSemanticNavigation({
        query: 'test',
        tenant_id: 'tenant',
      });
      expect(result.search_results).toEqual(['a']);
    });

    it('returns fallback when service fails', async () => {
      mockedAxios.post.mockRejectedValue(new Error('network'));
      const result = await controller.executeSemanticNavigation({
        query: 'test',
        tenant_id: 'tenant',
      });
      expect(result.search_results).toEqual([]);
      expect(result.metadata.error).toBeDefined();
    });
  });

  describe('findArchitecturalHotspots', () => {
    it('returns service data when call succeeds', async () => {
      mockedAxios.post.mockResolvedValue({
        data: { complexity_hotspots: [1] },
      });
      const result = await controller.findArchitecturalHotspots({
        tenant_id: 'tenant',
      });
      expect(result.complexity_hotspots).toEqual([1]);
    });

    it('returns fallback when service fails', async () => {
      mockedAxios.post.mockRejectedValue(new Error('network'));
      const result = await controller.findArchitecturalHotspots({
        tenant_id: 'tenant',
      });
      expect(result.complexity_hotspots).toEqual([]);
      expect(result.error).toBeDefined();
    });
  });

  describe('getPerformanceMetrics', () => {
    it('returns service data when call succeeds', async () => {
      mockedAxios.get.mockResolvedValue({
        data: { reasoning: { average_duration_ms: 5 } },
      });
      const result = await controller.getPerformanceMetrics();
      expect(result.reasoning.average_duration_ms).toBe(5);
    });

    it('returns fallback when service fails', async () => {
      mockedAxios.get.mockRejectedValue(new Error('network'));
      const result = await controller.getPerformanceMetrics();
      expect(result.reasoning).toBeDefined();
      expect(result.error).toBeDefined();
    });
  });
});
