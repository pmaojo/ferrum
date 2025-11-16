import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import {
  Github,
  Star,
  GitBranch,
  Calendar,
  Lock,
  Globe,
  Zap,
  Download,
} from 'lucide-react';

interface Repository {
  id: number;
  name: string;
  full_name: string;
  private: boolean;
  description: string;
  language: string;
  stargazers_count: number;
  updated_at: string;
  default_branch: string;
  clone_url: string;
}

interface GitHubIntegrationProps {
  onRepositoryAnalyze: (repoUrl: string, branch?: string) => void;
  isAnalyzing?: boolean;
}

export function GitHubIntegration({
  onRepositoryAnalyze,
  isAnalyzing = false,
}: GitHubIntegrationProps) {
  const [githubToken, setGithubToken] = useState('');
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [manualRepoUrl, setManualRepoUrl] = useState('');
  const { toast } = useToast();

  const fetchRepositories = async () => {
    if (!githubToken.trim()) {
      toast({
        title: 'GitHub Token Required',
        description:
          'Please provide your GitHub personal access token to connect repositories.',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(
        'https://api.github.com/user/repos?sort=updated&per_page=50',
        {
          headers: {
            Authorization: `token ${githubToken}`,
            Accept: 'application/vnd.github.v3+json',
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch repositories');
      }

      const repos = await response.json();
      setRepositories(repos);

      toast({
        title: '🚀 Repositories Loaded',
        description: `Found ${repos.length} repositories in your GitHub account.`,
      });
    } catch (error) {
      toast({
        title: 'Connection Failed',
        description:
          'Unable to connect to GitHub. Please check your token and try again.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const analyzeRepository = (repo: Repository) => {
    setSelectedRepo(repo);
    onRepositoryAnalyze(repo.clone_url, repo.default_branch);

    toast({
      title: '🌌 Scanning Repository',
      description: `Analyzing ${repo.name} with cosmic AST parsing...`,
    });
  };

  const analyzeManualRepo = () => {
    if (!manualRepoUrl.trim()) {
      toast({
        title: 'Repository URL Required',
        description: 'Please enter a valid GitHub repository URL.',
        variant: 'destructive',
      });
      return;
    }

    onRepositoryAnalyze(manualRepoUrl);

    toast({
      title: '🌌 Scanning Repository',
      description: 'Analyzing repository with cosmic AST parsing...',
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getLanguageColor = (language: string) => {
    const colors: Record<string, string> = {
      TypeScript: 'from-blue-400 to-blue-600',
      JavaScript: 'from-yellow-400 to-yellow-600',
      Python: 'from-green-400 to-green-600',
      Java: 'from-orange-400 to-orange-600',
      'C#': 'from-purple-400 to-purple-600',
      Go: 'from-cyan-400 to-cyan-600',
      Rust: 'from-red-400 to-red-600',
      PHP: 'from-indigo-400 to-indigo-600',
    };
    return colors[language] || 'from-gray-400 to-gray-600';
  };

  return (
    <div className="space-y-6">
      {/* GitHub Connection */}
      <Card className="hacker-border bg-card hacker-glow">
        <CardHeader>
          <CardTitle className="flex items-center space-x-3 text-primary hacker-text-glow terminal-font">
            <Github className="h-6 w-6 text-primary" />
            <span>GITHUB_REPO_SCANNER</span>
            <div className="ascii-art text-primary text-xs">[ONLINE]</div>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label
              htmlFor="github-token"
              className="text-primary terminal-font font-black hacker-text-glow"
            >
              ACCESS_TOKEN
            </Label>
            <Input
              id="github-token"
              type="password"
              value={githubToken}
              onChange={(e) => setGithubToken(e.target.value)}
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
              className="bg-input border-2 border-primary text-primary placeholder-primary/50 terminal-font hacker-glow"
            />
            <div className="text-xs text-primary/70 mt-2 terminal-font p-2 bg-primary/10 border border-primary">
              <span className="text-secondary">{'>'}</span> REQUIRED FOR PRIVATE
              REPOS{' '}
              <a
                href="https://github.com/settings/tokens"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline hover:text-primary/80 hacker-text-glow"
              >
                github.com/settings/tokens
              </a>
            </div>
          </div>

          <Button
            onClick={fetchRepositories}
            disabled={isLoading || !githubToken.trim()}
            className="bg-gradient-to-r from-purple-500 to-cyan-500 hover:from-purple-600 hover:to-cyan-600 text-white border-0"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                Scanning Repositories...
              </>
            ) : (
              <>
                <Zap className="h-4 w-4 mr-2" />
                Connect & Scan Repositories
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Manual Repository Input */}
      <Card className="border-2 border-cyan-500/30 bg-gradient-to-br from-slate-900/50 to-cyan-900/20 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center space-x-3 text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400">
            <GitBranch className="h-5 w-5 text-cyan-400" />
            <span>Direct Repository Analysis</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="repo-url" className="text-cyan-300">
              Repository URL
            </Label>
            <div className="flex space-x-2">
              <Input
                id="repo-url"
                value={manualRepoUrl}
                onChange={(e) => setManualRepoUrl(e.target.value)}
                placeholder="https://github.com/username/repository"
                className="bg-slate-800/50 border-cyan-500/30 text-cyan-100 placeholder-cyan-400/50"
              />
              <Button
                onClick={analyzeManualRepo}
                disabled={isAnalyzing || !manualRepoUrl.trim()}
                className="bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-600 hover:to-purple-600 text-white border-0"
              >
                {isAnalyzing ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Repository List */}
      {repositories.length > 0 && (
        <Card className="border-2 border-pink-500/30 bg-gradient-to-br from-slate-900/50 to-pink-900/20 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center space-x-3 text-transparent bg-clip-text bg-gradient-to-r from-pink-400 to-purple-400">
              <span>Your Repositories</span>
              <Badge
                variant="secondary"
                className="bg-pink-500/20 text-pink-300 border-pink-500/30"
              >
                {repositories.length} found
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar">
              {repositories.map((repo) => (
                <div
                  key={repo.id}
                  className={`p-4 rounded-lg border transition-all duration-300 cursor-pointer ${
                    selectedRepo?.id === repo.id
                      ? 'border-purple-400/50 bg-purple-500/10 shadow-lg shadow-purple-500/20'
                      : 'border-slate-600/30 bg-slate-800/30 hover:border-purple-400/30 hover:bg-purple-500/5'
                  }`}
                  onClick={() => analyzeRepository(repo)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <h3 className="font-semibold text-purple-100 truncate">
                          {repo.name}
                        </h3>
                        {repo.private ? (
                          <Lock className="h-4 w-4 text-yellow-400" />
                        ) : (
                          <Globe className="h-4 w-4 text-green-400" />
                        )}
                        {repo.language && (
                          <Badge
                            className={`text-xs bg-gradient-to-r ${getLanguageColor(repo.language)} text-white border-0`}
                          >
                            {repo.language}
                          </Badge>
                        )}
                      </div>

                      {repo.description && (
                        <p className="text-sm text-purple-300/80 mb-2 line-clamp-2">
                          {repo.description}
                        </p>
                      )}

                      <div className="flex items-center space-x-4 text-xs text-purple-400/70">
                        <div className="flex items-center space-x-1">
                          <Star className="h-3 w-3" />
                          <span>{repo.stargazers_count}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Calendar className="h-3 w-3" />
                          <span>{formatDate(repo.updated_at)}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <GitBranch className="h-3 w-3" />
                          <span>{repo.default_branch}</span>
                        </div>
                      </div>
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={isAnalyzing}
                      className="text-purple-400 hover:text-purple-300 hover:bg-purple-500/10"
                    >
                      {isAnalyzing && selectedRepo?.id === repo.id ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-purple-400 border-t-transparent" />
                      ) : (
                        <Zap className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
