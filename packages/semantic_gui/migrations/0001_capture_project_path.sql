ALTER TABLE "projects" ADD COLUMN "project_path" text;

UPDATE "projects"
SET "project_path" = COALESCE(
  metadata -> 'config' ->> 'projectPath',
  metadata ->> 'projectPath',
  metadata ->> 'path',
  '.'
);

ALTER TABLE "projects" ALTER COLUMN "project_path" SET NOT NULL;
