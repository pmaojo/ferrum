import { pgTable, text, jsonb, timestamp } from 'drizzle-orm/pg-core';
import { createInsertSchema } from 'drizzle-zod';
import { z } from 'zod';

// Graph Node Schema
export const graphNodes = pgTable('graph_nodes', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  type: text('type').notNull(), // usecase, adapter, entity, controller
  filePath: text('file_path'),
  description: text('description'),
  position: jsonb('position').$type<{ x: number; y: number }>().notNull(),
  metadata: jsonb('metadata').$type<Record<string, any>>().default({}),
  sourceMap: jsonb('source_map')
    .$type<{ file: string; line: number }>()
    .default({}),
  templateId: text('template_id').notNull(),
  projectId: text('project_id').notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

// Graph Edge Schema
export const graphEdges = pgTable('graph_edges', {
  id: text('id').primaryKey(),
  sourceNodeId: text('source_node_id').notNull(),
  targetNodeId: text('target_node_id').notNull(),
  type: text('type').notNull(), // depends, calls, implements, extends
  metadata: jsonb('metadata').$type<Record<string, any>>().default({}),
  projectId: text('project_id').notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

// Project Schema
export const projects = pgTable('projects', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  description: text('description'),
  templateId: text('template_id').notNull(),
  codebaseUrl: text('codebase_url'),
  projectPath: text('project_path').notNull(),
  metadata: jsonb('metadata').$type<Record<string, any>>().default({}),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

// Template Schema
export const templates = pgTable('templates', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  description: text('description'),
  extends: text('extends'),
  nodeTypes: jsonb('node_types')
    .$type<
      Array<{
        type: string;
        pattern: string;
        color: string;
        icon: string;
      }>
    >()
    .notNull(),
  relations: jsonb('relations')
    .$type<Array<{ source: string; target: string; type: string }>>()
    .default([]),
  validationRules: jsonb('validation_rules')
    .$type<
      Array<{
        rule: string;
        type: 'required' | 'prohibited';
        description: string;
      }>
    >()
    .notNull(),
  metadata: jsonb('metadata').$type<Record<string, any>>().default({}),
});

// Validation Result Schema
export const validationResults = pgTable('validation_results', {
  id: text('id').primaryKey(),
  projectId: text('project_id').notNull(),
  ruleId: text('rule_id').notNull(),
  status: text('status').notNull(), // valid, warning, violation
  sourceNodeId: text('source_node_id'),
  targetNodeId: text('target_node_id'),
  message: text('message').notNull(),
  metadata: jsonb('metadata').$type<Record<string, any>>().default({}),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// Insert Schemas
export const insertGraphNodeSchema = createInsertSchema(graphNodes).omit({
  createdAt: true,
  updatedAt: true,
});

export const insertGraphEdgeSchema = createInsertSchema(graphEdges)
  .omit({
    createdAt: true,
  })
  .extend({
    metadata: z.record(z.any()).optional(),
    parameters: z
      .array(
        z.object({
          name: z.string(),
          type: z.string(),
          direction: z.enum(['input', 'output', 'bidirectional']),
          dataType: z.string().optional(),
          required: z.boolean().optional(),
          description: z.string().optional(),
          defaultValue: z.any().optional(),
        })
      )
      .optional(),
    methodCalls: z
      .array(
        z.object({
          methodName: z.string(),
          parameters: z.array(z.string()).optional(),
          returnType: z.string().optional(),
        })
      )
      .optional(),
  });

export const insertProjectSchema = createInsertSchema(projects)
  .omit({
    id: true,
    createdAt: true,
    updatedAt: true,
    metadata: true,
  })
  .extend({
    metadata: z.record(z.any()).optional(),
  });

export const insertTemplateSchema = createInsertSchema(templates);

export const insertValidationResultSchema = createInsertSchema(
  validationResults
).omit({
  createdAt: true,
});

// Types
export type GraphNode = typeof graphNodes.$inferSelect;
export type GraphEdge = typeof graphEdges.$inferSelect;
export type Project = typeof projects.$inferSelect;
export type Template = typeof templates.$inferSelect;
export type ValidationResult = typeof validationResults.$inferSelect;

export type InsertGraphNode = z.infer<typeof insertGraphNodeSchema>;
export type InsertGraphEdge = z.infer<typeof insertGraphEdgeSchema>;
export type InsertProject = z.infer<typeof insertProjectSchema>;
export type InsertTemplate = z.infer<typeof insertTemplateSchema>;
export type InsertValidationResult = z.infer<
  typeof insertValidationResultSchema
>;
