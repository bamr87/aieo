import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Lightbulb, Plus, RefreshCw, Search } from 'lucide-react';
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  ErrorNote,
  Field,
  Input,
  Loading,
  PageHeader,
} from '../components/ui';
import { workspaceApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useToast } from '../hooks/useToast';
import { basename, formatDate, slugify } from '../lib/format';
import type { WorkspaceNode } from '../types';

interface Topic {
  path: string;
  slug: string;
  title: string;
}

/** Build a templated topic markdown file with frontmatter + heading. */
function topicTemplate(title: string): string {
  const today = new Date().toISOString().slice(0, 10);
  return `---
title: ${title}
status: idea
created: ${today}
keywords: []
---

# ${title}

## Why this topic matters

_Describe the angle, the audience, and why an AI engine would cite a page about this._

## Key questions to answer

-

## Notes

`;
}

function toTopic(node: WorkspaceNode): Topic {
  const slug = basename(node.path).replace(/\.md$/i, '');
  return {
    path: node.path,
    slug,
    title: slug.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
  };
}

export function TopicsPage() {
  const toast = useToast();
  const list = useAsyncAction();
  const add = useAsyncAction();

  const [topics, setTopics] = useState<Topic[]>([]);
  const [title, setTitle] = useState('');

  const load = async () => {
    const res = await list.run(async () => {
      await workspaceApi.init();
      return workspaceApi.tree();
    });
    if (!res) return;
    const found = res.nodes
      .filter((n) => n.type === 'file' && n.path.startsWith('topics/') && n.path.endsWith('.md'))
      .map(toTopic)
      .sort((a, b) => a.title.localeCompare(b.title));
    setTopics(found);
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = async () => {
    const trimmed = title.trim();
    if (!trimmed) return toast.error('Enter a topic title first');
    const slug = slugify(trimmed);
    const path = `topics/${slug}.md`;
    if (topics.some((t) => t.slug === slug)) {
      return toast.error(`A topic named "${slug}" already exists`);
    }
    const res = await add.run(() => workspaceApi.write(path, topicTemplate(trimmed)));
    if (!res) return;
    setTitle('');
    toast.success(`Added topic "${slug}"`);
    await load();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Topics"
        description="Capture content ideas as topics. Each is saved to topics/<slug>.md in the workspace, ready to research."
        actions={
          <Button
            variant="ghost"
            size="sm"
            onClick={load}
            loading={list.loading}
            leftIcon={<RefreshCw size={14} />}
          >
            Refresh
          </Button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
        {/* Add topic */}
        <Card className="self-start">
          <CardHeader title="Add a topic" description="Saved as a markdown file in topics/." />
          <CardBody className="space-y-4">
            <Field label="Topic title" hint="A short, descriptive headline for the idea.">
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    void submit();
                  }
                }}
                placeholder="How to choose an AI engine for content"
              />
            </Field>
            {title.trim() && (
              <p className="text-xs text-muted">
                File: <span className="font-medium text-ink">topics/{slugify(title)}.md</span>
              </p>
            )}
            <Button
              variant="primary"
              fullWidth
              loading={add.loading}
              onClick={submit}
              leftIcon={<Plus size={15} />}
            >
              Add topic
            </Button>
            {add.error && <ErrorNote message={add.error} onRetry={submit} />}
          </CardBody>
        </Card>

        {/* Topic list */}
        <div className="min-w-0">
          <Card>
            <CardHeader
              title="Your topics"
              description={topics.length ? `${topics.length} saved` : undefined}
            />
            <CardBody>
              {list.loading && topics.length === 0 ? (
                <Loading />
              ) : list.error ? (
                <ErrorNote message={list.error} onRetry={load} />
              ) : topics.length === 0 ? (
                <EmptyState
                  icon={<Lightbulb size={28} />}
                  title="No topics yet"
                  description="Add a topic on the left to start building your content pipeline."
                />
              ) : (
                <ul className="space-y-1.5">
                  {topics.map((topic) => (
                    <li
                      key={topic.path}
                      className="flex items-center gap-3 rounded-lg border border-line bg-elevated/40 px-3 py-2.5"
                    >
                      <FileText size={16} className="shrink-0 text-muted" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-ink">{topic.title}</p>
                        <p className="truncate text-xs text-muted">{basename(topic.path)}</p>
                      </div>
                      <Link
                        to="/research"
                        className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-line bg-card px-2.5 py-1.5 text-xs font-medium text-ink transition-colors hover:border-line-strong hover:text-brand"
                        title="Research this topic"
                      >
                        <Search size={13} />
                        Research
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
          {topics.length > 0 && (
            <p className="mt-3 px-1 text-xs text-muted">Last loaded {formatDate(Date.now())}.</p>
          )}
        </div>
      </div>
    </div>
  );
}
