import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  BarChart3,
  Bot,
  FileEdit,
  FilePlus2,
  FileText,
  FolderTree,
  Gauge,
  Layers,
  LayoutTemplate,
  Lightbulb,
  RefreshCw,
  Send,
  Sparkles,
  Target,
} from 'lucide-react';

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  description: string;
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Score & optimize',
    items: [
      { to: '/audit', label: 'Audit', icon: Gauge, description: 'Score content for AI citability' },
      { to: '/optimize', label: 'Optimize', icon: Sparkles, description: 'Rewrite content to lift the score' },
      { to: '/patterns', label: 'Patterns', icon: Layers, description: 'Browse the AIEO pattern library' },
      { to: '/agents', label: 'Agents', icon: Bot, description: 'Run specialized content agents' },
    ],
  },
  {
    title: 'Create',
    items: [
      { to: '/topics', label: 'Topics', icon: Lightbulb, description: 'Capture and manage topics' },
      { to: '/research', label: 'Research', icon: FileText, description: 'Generate research briefs' },
      { to: '/drafts', label: 'Drafts', icon: FilePlus2, description: 'Write and edit drafts' },
      { to: '/rewrites', label: 'Rewrites', icon: RefreshCw, description: 'Rewrite existing drafts' },
      { to: '/landing-pages', label: 'Landing', icon: LayoutTemplate, description: 'Landing-page workflows' },
      { to: '/workspace', label: 'Workspace', icon: FolderTree, description: 'Browse & edit workspace files' },
    ],
  },
  {
    title: 'Analyze & publish',
    items: [
      { to: '/dashboard', label: 'Citations', icon: BarChart3, description: 'Citation share-of-voice' },
      { to: '/performance', label: 'Performance', icon: Activity, description: 'GA4 / GSC / SERP data' },
      { to: '/published', label: 'Published', icon: Send, description: 'Published artifacts & publishing' },
    ],
  },
];

export const ALL_NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

// Re-exported so non-nav surfaces (e.g. HomePage) can reuse icons.
export { FileEdit, Target };
