import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { 
  Users, 
  Edit3, 
  Eye, 
  MessageSquare, 
  Clock, 
  AlertTriangle,
  CheckCircle,
  X,
  Send,
  Lock,
  Unlock,
  GitMerge,
  RefreshCw
} from 'lucide-react';
import { useRealtimeSync } from '@/hooks/useRealtimeSync';
import { formatDistanceToNow } from 'date-fns';

interface CollaborativeUser {
  id: string;
  name: string;
  avatar?: string;
  color: string;
  isActive: boolean;
  lastSeen: string;
  currentFile?: string;
  cursor?: {
    line: number;
    column: number;
  };
}

interface EditConflict {
  id: string;
  fileId: string;
  fileName: string;
  conflictType: 'concurrent_edit' | 'version_mismatch' | 'lock_conflict';
  users: string[];
  timestamp: string;
  resolved: boolean;
  resolution?: 'merge' | 'override' | 'manual';
}

interface CollaborativeEditingSystemProps {
  projectId: string;
  currentUserId: string;
  currentUserName: string;
  className?: string;
}

/**
 * @kthulu:extend - Collaborative editing system for real-time Kthulu development
 * Handles multi-user editing, conflict resolution, and real-time synchronization
 */
export function CollaborativeEditingSystem({
  projectId,
  currentUserId,
  currentUserName,
  className
}: CollaborativeEditingSystemProps) {
  const [activeUsers, setActiveUsers] = useState([] as CollaborativeUser[]);
  const [conflicts, setConflicts] = useState([] as EditConflict[]);
  const [selectedConflict, setSelectedConflict] = useState(null as EditConflict | null);
  const [chatMessages, setChatMessages] = useState([] as any[]);
  const [newMessage, setNewMessage] = useState('');
  const [isTyping, setIsTyping] = useState([] as string[]);
  const [lockedFiles, setLockedFiles] = useState({} as Record<string, string>);

  const typingTimeoutRef = useRef(null as any);
  
  const {
    isConnected,
    events,
    lastEvent
  } = useRealtimeSync({
    projectId,
    subscriptions: ['collaboration_event', 'file_locked', 'file_unlocked', 'conflict_detected', 'conflict_resolved'],
    onEvent: handleCollaborationEvent
  });
  
  function handleCollaborationEvent(event: any) {
    switch (event.eventType) {
      case 'user_joined':
        handleUserJoined(event.data);
        break;
      case 'user_left':
        handleUserLeft(event.data);
        break;
      case 'user_editing':
        handleUserEditing(event.data);
        break;
      case 'conflict_detected':
        handleConflictDetected(event.data);
        break;
      case 'conflict_resolved':
        handleConflictResolved(event.data);
        break;
      case 'file_locked':
        handleFileLocked(event.data);
        break;
      case 'file_unlocked':
        handleFileUnlocked(event.data);
        break;
      case 'chat_message':
        handleChatMessage(event.data);
        break;
      case 'user_typing':
        handleUserTyping(event.data);
        break;
    }
  }
  
  const handleUserJoined = useCallback((data: any) => {
    const newUser: CollaborativeUser = {
      id: data.userId,
      name: data.userName,
      avatar: data.avatar,
      color: data.color || generateUserColor(data.userId),
      isActive: true,
      lastSeen: new Date().toISOString()
    };
    
    setActiveUsers(prev => {
      const existing = prev.find(u => u.id === newUser.id);
      if (existing) {
        return prev.map(u => u.id === newUser.id ? { ...u, isActive: true, lastSeen: newUser.lastSeen } : u);
      }
      return [...prev, newUser];
    });
  }, []);
  
  const handleUserLeft = useCallback((data: any) => {
    setActiveUsers(prev => 
      prev.map(u => 
        u.id === data.userId 
          ? { ...u, isActive: false, lastSeen: new Date().toISOString() }
          : u
      )
    );
  }, []);
  
  const handleUserEditing = useCallback((data: any) => {
    setActiveUsers(prev => 
      prev.map(u => 
        u.id === data.userId 
          ? { 
              ...u, 
              currentFile: data.fileName,
              cursor: data.cursor,
              lastSeen: new Date().toISOString()
            }
          : u
      )
    );
  }, []);
  
  const handleConflictDetected = useCallback((data: any) => {
    const conflict: EditConflict = {
      id: data.conflictId,
      fileId: data.fileId,
      fileName: data.fileName,
      conflictType: data.conflictType,
      users: data.users,
      timestamp: new Date().toISOString(),
      resolved: false
    };
    
    setConflicts(prev => [...prev, conflict]);
  }, []);
  
  const handleConflictResolved = useCallback((data: any) => {
    setConflicts(prev => 
      prev.map(c => 
        c.id === data.conflictId 
          ? { ...c, resolved: true, resolution: data.resolution }
          : c
      )
    );
  }, []);
  
  const handleFileLocked = useCallback((data: any) => {
    setLockedFiles(prev => ({
      ...prev,
      [data.fileId]: data.userId
    }));
  }, []);
  
  const handleFileUnlocked = useCallback((data: any) => {
    setLockedFiles(prev => {
      const updated = { ...prev };
      delete updated[data.fileId];
      return updated;
    });
  }, []);
  
  const handleChatMessage = useCallback((data: any) => {
    setChatMessages(prev => [...prev, {
      id: data.messageId,
      userId: data.userId,
      userName: data.userName,
      message: data.message,
      timestamp: data.timestamp
    }]);
  }, []);
  
  const handleUserTyping = useCallback((data: any) => {
    setIsTyping(prev => {
      if (data.isTyping) {
        return prev.includes(data.userId) ? prev : [...prev, data.userId];
      } else {
        return prev.filter(id => id !== data.userId);
      }
    });
    
    // Clear typing indicator after timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    
    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(prev => prev.filter(id => id !== data.userId));
    }, 3000);
  }, []);
  
  const generateUserColor = (userId: string): string => {
    const colors = [
      '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
      '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
    ];
    const hash = userId.split('').reduce((a, b) => {
      a = ((a << 5) - a) + b.charCodeAt(0);
      return a & a;
    }, 0);
    return colors[Math.abs(hash) % colors.length];
  };
  
  const sendChatMessage = useCallback(() => {
    if (!newMessage.trim() || !isConnected) return;
    
    // In a real implementation, this would send via WebSocket
    const message = {
      type: 'chat_message',
      projectId,
      userId: currentUserId,
      userName: currentUserName,
      message: newMessage.trim(),
      timestamp: new Date().toISOString()
    };
    
    // Simulate sending message
    handleChatMessage({
      messageId: Date.now().toString(),
      ...message
    });
    
    setNewMessage('');
  }, [newMessage, isConnected, projectId, currentUserId, currentUserName]);
  
  const resolveConflict = useCallback((conflictId: string, resolution: 'merge' | 'override' | 'manual') => {
    // In a real implementation, this would resolve the conflict via API
    handleConflictResolved({
      conflictId,
      resolution,
      resolvedBy: currentUserId,
      timestamp: new Date().toISOString()
    });
    
    setSelectedConflict(null);
  }, [currentUserId]);
  
  const lockFile = useCallback((fileId: string) => {
    // In a real implementation, this would lock the file via API
    handleFileLocked({
      fileId,
      userId: currentUserId,
      timestamp: new Date().toISOString()
    });
  }, [currentUserId]);
  
  const unlockFile = useCallback((fileId: string) => {
    // In a real implementation, this would unlock the file via API
    handleFileUnlocked({
      fileId,
      userId: currentUserId,
      timestamp: new Date().toISOString()
    });
  }, [currentUserId]);
  
  const activeConflicts = conflicts.filter(c => !c.resolved);
  const resolvedConflicts = conflicts.filter(c => c.resolved);
  
  return (
    <div className={`space-y-6 ${className}`}>
      {/* Active Users */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Users className="h-5 w-5" />
              <CardTitle className="text-lg">Active Collaborators</CardTitle>
              <Badge variant="outline">{activeUsers.filter(u => u.isActive).length} online</Badge>
            </div>
            <div className="flex items-center space-x-1">
              {isConnected ? (
                <Badge variant="default" className="bg-green-100 text-green-800">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse" />
                  Connected
                </Badge>
              ) : (
                <Badge variant="destructive">Disconnected</Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {activeUsers.map(user => (
              <div 
                key={user.id} 
                className={`flex items-center space-x-2 p-2 rounded-lg border ${
                  user.isActive ? 'bg-white' : 'bg-gray-50 opacity-60'
                }`}
              >
                <div className="relative">
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user.avatar} />
                    <AvatarFallback style={{ backgroundColor: user.color, color: 'white' }}>
                      {user.name.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  {user.isActive && (
                    <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
                  )}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{user.name}</p>
                  <div className="flex items-center space-x-1 text-xs text-gray-500">
                    {user.currentFile ? (
                      <>
                        <Edit3 className="h-3 w-3" />
                        <span className="truncate">{user.currentFile}</span>
                      </>
                    ) : (
                      <>
                        <Eye className="h-3 w-3" />
                        <span>Viewing</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {activeUsers.length === 0 && (
              <p className="text-sm text-gray-500">No other collaborators online</p>
            )}
          </div>
        </CardContent>
      </Card>
      
      {/* Conflicts Panel */}
      {activeConflicts.length > 0 && (
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader className="pb-3">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-orange-600" />
              <CardTitle className="text-lg text-orange-800">Edit Conflicts</CardTitle>
              <Badge variant="destructive">{activeConflicts.length}</Badge>
            </div>
            <CardDescription className="text-orange-700">
              Resolve conflicts to continue collaborative editing
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {activeConflicts.map(conflict => (
                <div key={conflict.id} className="bg-white p-3 rounded-lg border border-orange-200">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-sm">{conflict.fileName}</span>
                        <Badge variant="outline" className="text-xs">
                          {conflict.conflictType.replace('_', ' ')}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-600 mt-1">
                        Conflict between: {conflict.users.join(', ')}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatDistanceToNow(new Date(conflict.timestamp), { addSuffix: true })}
                      </p>
                    </div>
                    <div className="flex space-x-2">
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => setSelectedConflict(conflict)}
                      >
                        Resolve
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Conflict Resolution Modal */}
      {selectedConflict && (
        <Card className="border-2 border-orange-300">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Resolve Conflict</CardTitle>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setSelectedConflict(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <CardDescription>
              File: {selectedConflict.fileName} • Type: {selectedConflict.conflictType}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <Button 
                  variant="outline" 
                  className="flex items-center space-x-2"
                  onClick={() => resolveConflict(selectedConflict.id, 'merge')}
                >
                  <GitMerge className="h-4 w-4" />
                  <span>Auto Merge</span>
                </Button>
                <Button 
                  variant="outline" 
                  className="flex items-center space-x-2"
                  onClick={() => resolveConflict(selectedConflict.id, 'override')}
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>Override</span>
                </Button>
                <Button 
                  variant="outline" 
                  className="flex items-center space-x-2"
                  onClick={() => resolveConflict(selectedConflict.id, 'manual')}
                >
                  <Edit3 className="h-4 w-4" />
                  <span>Manual Edit</span>
                </Button>
              </div>
              <div className="text-sm text-gray-600">
                <p><strong>Auto Merge:</strong> Automatically combine changes where possible</p>
                <p><strong>Override:</strong> Use your version and discard others</p>
                <p><strong>Manual Edit:</strong> Open editor to resolve manually</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* File Locks */}
      {Object.keys(lockedFiles).length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center space-x-2">
              <Lock className="h-5 w-5" />
              <CardTitle className="text-lg">Locked Files</CardTitle>
              <Badge variant="outline">{Object.keys(lockedFiles).length}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(lockedFiles).map(([fileId, userId]) => {
                const user = activeUsers.find(u => u.id === userId);
                return (
                  <div key={fileId} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <div className="flex items-center space-x-2">
                      <Lock className="h-4 w-4 text-gray-500" />
                      <span className="text-sm font-medium">{fileId}</span>
                      <span className="text-xs text-gray-500">
                        locked by {user?.name || userId}
                      </span>
                    </div>
                    {userId === currentUserId && (
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => unlockFile(fileId)}
                      >
                        <Unlock className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Team Chat */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center space-x-2">
            <MessageSquare className="h-5 w-5" />
            <CardTitle className="text-lg">Team Chat</CardTitle>
            {isTyping.length > 0 && (
              <Badge variant="outline" className="text-xs">
                {isTyping.length} typing...
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <ScrollArea className="h-48 border rounded-md p-3">
              {chatMessages.map(msg => {
                const user = activeUsers.find(u => u.id === msg.userId);
                return (
                  <div key={msg.id} className="flex space-x-2 mb-3">
                    <Avatar className="h-6 w-6 mt-1">
                      <AvatarImage src={user?.avatar} />
                      <AvatarFallback 
                        style={{ backgroundColor: user?.color || '#gray', color: 'white' }}
                        className="text-xs"
                      >
                        {msg.userName.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-medium">{msg.userName}</span>
                        <span className="text-xs text-gray-500">
                          {formatDistanceToNow(new Date(msg.timestamp), { addSuffix: true })}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 mt-1">{msg.message}</p>
                    </div>
                  </div>
                );
              })}
              {chatMessages.length === 0 && (
                <p className="text-sm text-gray-500 text-center py-4">No messages yet</p>
              )}
            </ScrollArea>
            
            <div className="flex space-x-2">
              <Input
                placeholder="Type a message..."
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
                disabled={!isConnected}
              />
              <Button 
                onClick={sendChatMessage}
                disabled={!newMessage.trim() || !isConnected}
                size="sm"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Recent Activity */}
      {resolvedConflicts.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <CardTitle className="text-lg">Recently Resolved</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {resolvedConflicts.slice(0, 5).map(conflict => (
                <div key={conflict.id} className="flex items-center justify-between p-2 bg-green-50 rounded border border-green-200">
                  <div>
                    <span className="text-sm font-medium">{conflict.fileName}</span>
                    <span className="text-xs text-gray-500 ml-2">
                      resolved by {conflict.resolution}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {formatDistanceToNow(new Date(conflict.timestamp), { addSuffix: true })}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}