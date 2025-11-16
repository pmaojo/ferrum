CREATE TABLE "graph_edges" (
	"id" text PRIMARY KEY NOT NULL,
	"source_node_id" text NOT NULL,
	"target_node_id" text NOT NULL,
	"type" text NOT NULL,
	"metadata" jsonb DEFAULT '{}'::jsonb,
	"project_id" text NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "graph_nodes" (
	"id" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"type" text NOT NULL,
	"file_path" text,
	"description" text,
	"position" jsonb NOT NULL,
	"metadata" jsonb DEFAULT '{}'::jsonb,
	"template_id" text NOT NULL,
	"project_id" text NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "projects" (
	"id" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"description" text,
	"template_id" text NOT NULL,
	"codebase_url" text,
	"metadata" jsonb DEFAULT '{}'::jsonb,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "templates" (
	"id" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"description" text,
	"node_types" jsonb NOT NULL,
	"validation_rules" jsonb NOT NULL,
	"metadata" jsonb DEFAULT '{}'::jsonb
);
--> statement-breakpoint
CREATE TABLE "validation_results" (
	"id" text PRIMARY KEY NOT NULL,
	"project_id" text NOT NULL,
	"rule_id" text NOT NULL,
	"status" text NOT NULL,
	"source_node_id" text,
	"target_node_id" text,
	"message" text NOT NULL,
	"metadata" jsonb DEFAULT '{}'::jsonb,
	"created_at" timestamp DEFAULT now() NOT NULL
);
