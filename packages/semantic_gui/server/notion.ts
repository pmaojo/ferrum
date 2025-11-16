import { Client } from '@notionhq/client';

import { env } from './config';

// Initialize Notion client
export const notion = new Client({
  auth: env.NOTION_INTEGRATION_SECRET!,
});

// Extract the page ID from the Notion page URL
function extractPageIdFromUrl(pageUrl: string): string {
  const match = pageUrl.match(/([a-f0-9]{32})(?:[?#]|$)/i);
  if (match && match[1]) {
    return match[1];
  }
  throw Error('Failed to extract page ID');
}

export const NOTION_PAGE_ID = env.NOTION_PAGE_URL
  ? extractPageIdFromUrl(env.NOTION_PAGE_URL)
  : null;

/**
 * Lists all child databases contained within NOTION_PAGE_ID
 */
export async function getNotionDatabases() {
  if (!NOTION_PAGE_ID) return [];

  const childDatabases = [];

  try {
    let hasMore = true;
    let startCursor: string | undefined = undefined;

    while (hasMore) {
      const response = await notion.blocks.children.list({
        block_id: NOTION_PAGE_ID,
        start_cursor: startCursor,
      });

      for (const block of response.results) {
        if (block.type === 'child_database') {
          const databaseId = block.id;

          try {
            const databaseInfo = await notion.databases.retrieve({
              database_id: databaseId,
            });
            childDatabases.push(databaseInfo);
          } catch (error) {
            console.error(`Error retrieving database ${databaseId}:`, error);
          }
        }
      }

      hasMore = response.has_more;
      startCursor = response.next_cursor || undefined;
    }

    return childDatabases;
  } catch (error) {
    console.error('Error listing child databases:', error);
    throw error;
  }
}

// Find database by title
export async function findDatabaseByTitle(title: string) {
  const databases = await getNotionDatabases();

  for (const db of databases) {
    if (db.title && Array.isArray(db.title) && db.title.length > 0) {
      const dbTitle = db.title[0]?.plain_text?.toLowerCase() || '';
      if (dbTitle === title.toLowerCase()) {
        return db;
      }
    }
  }

  return null;
}

// Create database if it doesn't exist
export async function createDatabaseIfNotExists(
  title: string,
  properties: any
) {
  if (!NOTION_PAGE_ID) {
    throw new Error('Notion integration not configured');
  }

  const existingDb = await findDatabaseByTitle(title);
  if (existingDb) {
    return existingDb;
  }

  return await notion.databases.create({
    parent: {
      type: 'page_id',
      page_id: NOTION_PAGE_ID,
    },
    title: [
      {
        type: 'text',
        text: {
          content: title,
        },
      },
    ],
    properties,
  });
}

// Store project analysis in Notion
export async function storeProjectAnalysis(projectData: {
  name: string;
  template: string;
  nodeCount: number;
  edgeCount: number;
  complexity: string;
  insights: string[];
  validationIssues: number;
}) {
  if (!NOTION_PAGE_ID) {
    console.warn('Notion integration not configured - skipping storage');
    return;
  }

  try {
    const database = await createDatabaseIfNotExists(
      'Code Architecture Analysis',
      {
        Name: { title: {} },
        Template: { select: { options: [] } },
        NodeCount: { number: {} },
        EdgeCount: { number: {} },
        Complexity: {
          select: {
            options: [
              { name: 'Low', color: 'green' },
              { name: 'Medium', color: 'yellow' },
              { name: 'High', color: 'orange' },
              { name: 'Critical', color: 'red' },
            ],
          },
        },
        ValidationIssues: { number: {} },
        Insights: { rich_text: {} },
        AnalyzedAt: { date: {} },
      }
    );

    await notion.pages.create({
      parent: { database_id: database.id },
      properties: {
        Name: {
          title: [{ text: { content: projectData.name } }],
        },
        Template: {
          select: { name: projectData.template },
        },
        NodeCount: {
          number: projectData.nodeCount,
        },
        EdgeCount: {
          number: projectData.edgeCount,
        },
        Complexity: {
          select: { name: projectData.complexity },
        },
        ValidationIssues: {
          number: projectData.validationIssues,
        },
        Insights: {
          rich_text: [
            {
              text: {
                content: projectData.insights.join('\n• '),
              },
            },
          ],
        },
        AnalyzedAt: {
          date: { start: new Date().toISOString() },
        },
      },
    });

    console.log('Project analysis stored in Notion successfully');
  } catch (error) {
    console.error('Failed to store analysis in Notion:', error);
  }
}

// Store AI insights in Notion
export async function storeAIInsights(insights: {
  projectName: string;
  summary: string;
  recommendations: string[];
  threats: string[];
  optimizations: string[];
  complexity: string;
}) {
  if (!NOTION_PAGE_ID) {
    console.warn(
      'Notion integration not configured - skipping AI insights storage'
    );
    return;
  }

  try {
    const database = await createDatabaseIfNotExists(
      'AI Architecture Insights',
      {
        ProjectName: { title: {} },
        Summary: { rich_text: {} },
        Complexity: {
          select: {
            options: [
              { name: 'Low', color: 'green' },
              { name: 'Medium', color: 'yellow' },
              { name: 'High', color: 'orange' },
              { name: 'Critical', color: 'red' },
            ],
          },
        },
        Recommendations: { rich_text: {} },
        Threats: { rich_text: {} },
        Optimizations: { rich_text: {} },
        GeneratedAt: { date: {} },
      }
    );

    await notion.pages.create({
      parent: { database_id: database.id },
      properties: {
        ProjectName: {
          title: [{ text: { content: insights.projectName } }],
        },
        Summary: {
          rich_text: [{ text: { content: insights.summary } }],
        },
        Complexity: {
          select: { name: insights.complexity },
        },
        Recommendations: {
          rich_text: [
            {
              text: {
                content: insights.recommendations.join('\n• '),
              },
            },
          ],
        },
        Threats: {
          rich_text: [
            {
              text: {
                content: insights.threats.join('\n• '),
              },
            },
          ],
        },
        Optimizations: {
          rich_text: [
            {
              text: {
                content: insights.optimizations.join('\n• '),
              },
            },
          ],
        },
        GeneratedAt: {
          date: { start: new Date().toISOString() },
        },
      },
    });

    console.log('AI insights stored in Notion successfully');
  } catch (error) {
    console.error('Failed to store AI insights in Notion:', error);
  }
}
