import React from 'react';
import { Link, useLocation } from 'wouter';
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
} from '@/components/ui/navigation-menu';
import { Button } from '@/components/ui/button';
import {
  Monitor,
  Code,
  Database,
  Users,
  Settings,
  Home,
  Layers,
  Zap,
  Terminal,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavigationItem {
  title: string;
  href: string;
  description: string;
  icon: React.ReactNode;
}

const navigationItems: NavigationItem[] = [
  {
    title: 'Graph Editor',
    href: '/',
    description: 'Visual architecture editor and code graph interface',
    icon: <Code className="h-4 w-4" />,
  },
  {
    title: 'Development Dashboard',
    href: '/dashboard',
    description: 'Unified development environment and service monitoring',
    icon: <Monitor className="h-4 w-4" />,
  },
  {
    title: 'Templates',
    href: '/templates',
    description: 'Architecture templates and scaffolding marketplace',
    icon: <Layers className="h-4 w-4" />,
  },
  {
    title: 'PermaGraph',
    href: '/permagraph',
    description: 'Semantic graph storage and knowledge management',
    icon: <Database className="h-4 w-4" />,
  },
  {
    title: 'Agents',
    href: '/agents',
    description: 'AI agent management and configuration',
    icon: <Users className="h-4 w-4" />,
  },
];

const frameworkItems: NavigationItem[] = [
  {
    title: 'Ferrum',
    href: '/dashboard?framework=ferrum',
    description: 'AI-first scaffolding with Rust/React stack',
    icon: <Zap className="h-4 w-4" />,
  },
  {
    title: 'Kthulu',
    href: '/dashboard?framework=kthulu',
    description: 'Go backend with React frontend',
    icon: <Code className="h-4 w-4" />,
  },
  {
    title: 'Tuetano',
    href: '/dashboard?framework=tuetano',
    description: 'C++ framework for high-performance applications',
    icon: <Terminal className="h-4 w-4" />,
  },
];

export function MainNavigationMenu() {
  const [location] = useLocation();

  return (
    <div className="flex items-center space-x-4 p-4 border-b">
      <div className="flex items-center space-x-2">
        <Home className="h-6 w-6" />
        <span className="font-bold text-lg">ZHUL_SYS_</span>
      </div>
      
      <NavigationMenu>
        <NavigationMenuList>
          <NavigationMenuItem>
            <NavigationMenuTrigger>Navigation</NavigationMenuTrigger>
            <NavigationMenuContent>
              <ul className="grid w-[400px] gap-3 p-4 md:w-[500px] md:grid-cols-2 lg:w-[600px]">
                {navigationItems.map((item) => (
                  <ListItem
                    key={item.title}
                    title={item.title}
                    href={item.href}
                    icon={item.icon}
                    isActive={location === item.href}
                  >
                    {item.description}
                  </ListItem>
                ))}
              </ul>
            </NavigationMenuContent>
          </NavigationMenuItem>
          
          <NavigationMenuItem>
            <NavigationMenuTrigger>Frameworks</NavigationMenuTrigger>
            <NavigationMenuContent>
              <ul className="grid w-[400px] gap-3 p-4 md:w-[500px] md:grid-cols-1 lg:w-[600px]">
                {frameworkItems.map((item) => (
                  <ListItem
                    key={item.title}
                    title={item.title}
                    href={item.href}
                    icon={item.icon}
                    isActive={location.includes(item.href)}
                  >
                    {item.description}
                  </ListItem>
                ))}
              </ul>
            </NavigationMenuContent>
          </NavigationMenuItem>
        </NavigationMenuList>
      </NavigationMenu>

      <div className="flex-1" />
      
      <div className="flex items-center space-x-2">
        <Button
          variant={location === '/dashboard' ? 'default' : 'ghost'}
          size="sm"
          asChild
        >
          <Link href="/dashboard">
            <Monitor className="h-4 w-4 mr-2" />
            Dashboard
          </Link>
        </Button>
        
        <Button
          variant={location === '/' ? 'default' : 'ghost'}
          size="sm"
          asChild
        >
          <Link href="/">
            <Code className="h-4 w-4 mr-2" />
            Graph Editor
          </Link>
        </Button>
      </div>
    </div>
  );
}

interface ListItemProps {
  title: string;
  href: string;
  children: React.ReactNode;
  icon: React.ReactNode;
  isActive?: boolean;
}

const ListItem = React.forwardRef<
  React.ElementRef<typeof Link>,
  ListItemProps
>(({ title, href, children, icon, isActive, ...props }, ref) => {
  return (
    <li>
      <NavigationMenuLink asChild>
        <Link
          ref={ref}
          href={href}
          className={cn(
            'block select-none space-y-1 rounded-md p-3 leading-none no-underline outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground',
            isActive && 'bg-accent text-accent-foreground'
          )}
          {...props}
        >
          <div className="flex items-center space-x-2">
            {icon}
            <div className="text-sm font-medium leading-none">{title}</div>
          </div>
          <p className="line-clamp-2 text-sm leading-snug text-muted-foreground">
            {children}
          </p>
        </Link>
      </NavigationMenuLink>
    </li>
  );
});
ListItem.displayName = 'ListItem';