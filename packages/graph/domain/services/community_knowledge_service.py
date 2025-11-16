"""
Community Knowledge Sharing Service

Manages community-contributed architectural patterns, best practices,
and knowledge sharing features. Enables collaborative learning and
pattern evolution through community feedback and contributions.
"""

from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import hashlib

from .architectural_pattern_library import ArchitecturalPattern, PatternCategory, PatternComplexity
from .best_practices_knowledge_graph import BestPractice, PracticeType, PracticeContext, EvidenceLevel


class ContributionType(Enum):
    PATTERN = "pattern"
    PRACTICE = "practice"
    EXAMPLE = "example"
    EVIDENCE = "evidence"
    REVIEW = "review"
    DISCUSSION = "discussion"


class ContributionStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ReviewStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CHANGES = "needs_changes"


@dataclass
class CommunityUser:
    """Represents a community user"""
    id: str
    username: str
    email: str
    reputation: int = 0
    expertise_areas: Set[str] = field(default_factory=set)
    contributions_count: int = 0
    reviews_count: int = 0
    joined_at: datetime = field(default_factory=datetime.now)
    is_expert: bool = False
    is_moderator: bool = False


@dataclass
class ContributionReview:
    """Review of a community contribution"""
    id: str
    contribution_id: str
    reviewer_id: str
    status: ReviewStatus
    rating: int  # 1-5 stars
    comments: str
    suggestions: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class CommunityContribution:
    """Represents a community contribution"""
    id: str
    contributor_id: str
    contribution_type: ContributionType
    status: ContributionStatus
    title: str
    description: str
    content: Dict[str, Any]  # The actual pattern/practice/example content
    tags: Set[str] = field(default_factory=set)
    category: Optional[str] = None
    reviews: List[ContributionReview] = field(default_factory=list)
    upvotes: int = 0
    downvotes: int = 0
    view_count: int = 0
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None


@dataclass
class KnowledgeDiscussion:
    """Discussion thread about patterns or practices"""
    id: str
    title: str
    content: str
    author_id: str
    related_pattern_ids: List[str] = field(default_factory=list)
    related_practice_ids: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    replies: List['DiscussionReply'] = field(default_factory=list)
    upvotes: int = 0
    downvotes: int = 0
    view_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_pinned: bool = False
    is_closed: bool = False


@dataclass
class DiscussionReply:
    """Reply to a knowledge discussion"""
    id: str
    discussion_id: str
    author_id: str
    content: str
    parent_reply_id: Optional[str] = None
    upvotes: int = 0
    downvotes: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_accepted_answer: bool = False


class CommunityKnowledgeService:
    """Service for managing community knowledge sharing"""
    
    def __init__(self):
        self.users: Dict[str, CommunityUser] = {}
        self.contributions: Dict[str, CommunityContribution] = {}
        self.discussions: Dict[str, KnowledgeDiscussion] = {}
        self.reviews: Dict[str, ContributionReview] = {}
        
        # Indices for efficient searching
        self.contributions_by_user: Dict[str, Set[str]] = {}
        self.contributions_by_type: Dict[ContributionType, Set[str]] = {}
        self.contributions_by_status: Dict[ContributionStatus, Set[str]] = {}
        self.contributions_by_tag: Dict[str, Set[str]] = {}
        
        self._initialize_default_users()
    
    def _initialize_default_users(self):
        """Initialize some default expert users"""
        experts = [
            CommunityUser(
                id="expert_1",
                username="arch_guru",
                email="expert1@example.com",
                reputation=1000,
                expertise_areas={"hexagonal_architecture", "ddd", "clean_architecture"},
                is_expert=True,
                is_moderator=True
            ),
            CommunityUser(
                id="expert_2",
                username="pattern_master",
                email="expert2@example.com",
                reputation=850,
                expertise_areas={"design_patterns", "solid_principles", "refactoring"},
                is_expert=True
            )
        ]
        
        for expert in experts:
            self.users[expert.id] = expert
    
    def register_user(self, username: str, email: str) -> CommunityUser:
        """Register a new community user"""
        user_id = self._generate_id(f"user_{username}_{email}")
        
        user = CommunityUser(
            id=user_id,
            username=username,
            email=email
        )
        
        self.users[user_id] = user
        self.contributions_by_user[user_id] = set()
        
        return user
    
    def submit_contribution(
        self,
        contributor_id: str,
        contribution_type: ContributionType,
        title: str,
        description: str,
        content: Dict[str, Any],
        tags: Optional[Set[str]] = None,
        category: Optional[str] = None
    ) -> CommunityContribution:
        """Submit a new contribution to the community"""
        
        if contributor_id not in self.users:
            raise ValueError("Contributor not found")
        
        contribution_id = self._generate_id(f"contrib_{title}_{contributor_id}")
        
        contribution = CommunityContribution(
            id=contribution_id,
            contributor_id=contributor_id,
            contribution_type=contribution_type,
            status=ContributionStatus.SUBMITTED,
            title=title,
            description=description,
            content=content,
            tags=tags or set(),
            category=category
        )
        
        self.contributions[contribution_id] = contribution
        self.contributions_by_user[contributor_id].add(contribution_id)
        self._update_contribution_indices(contribution)
        
        # Update user stats
        self.users[contributor_id].contributions_count += 1
        
        return contribution
    
    def submit_pattern_contribution(
        self,
        contributor_id: str,
        pattern: ArchitecturalPattern
    ) -> CommunityContribution:
        """Submit an architectural pattern as a contribution"""
        
        content = {
            "pattern_data": {
                "name": pattern.name,
                "category": pattern.category.value,
                "complexity": pattern.complexity.value,
                "description": pattern.description,
                "intent": pattern.intent,
                "structure": pattern.structure,
                "participants": pattern.participants,
                "collaborations": pattern.collaborations,
                "consequences": pattern.consequences,
                "implementation_notes": pattern.implementation_notes,
                "examples": [
                    {
                        "language": ex.language,
                        "code_snippet": ex.code_snippet,
                        "description": ex.description,
                        "file_structure": ex.file_structure
                    }
                    for ex in pattern.examples
                ],
                "common_violations": [
                    {
                        "violation_type": v.violation_type,
                        "description": v.description,
                        "example": v.example,
                        "fix_suggestion": v.fix_suggestion,
                        "severity": v.severity
                    }
                    for v in pattern.common_violations
                ],
                "related_patterns": pattern.related_patterns,
                "owl_axioms": pattern.owl_axioms
            }
        }
        
        return self.submit_contribution(
            contributor_id=contributor_id,
            contribution_type=ContributionType.PATTERN,
            title=f"Pattern: {pattern.name}",
            description=pattern.description,
            content=content,
            tags=pattern.tags,
            category=pattern.category.value
        )
    
    def submit_practice_contribution(
        self,
        contributor_id: str,
        practice: BestPractice
    ) -> CommunityContribution:
        """Submit a best practice as a contribution"""
        
        content = {
            "practice_data": {
                "name": practice.name,
                "practice_type": practice.practice_type.value,
                "context": [ctx.value for ctx in practice.context],
                "description": practice.description,
                "rationale": practice.rationale,
                "when_to_apply": practice.when_to_apply,
                "when_not_to_apply": practice.when_not_to_apply,
                "implementation_steps": practice.implementation_steps,
                "code_examples": practice.code_examples,
                "detection_rules": practice.detection_rules,
                "metrics": practice.metrics,
                "evidence": [
                    {
                        "source": ev.source,
                        "evidence_type": ev.evidence_type.value,
                        "description": ev.description,
                        "url": ev.url,
                        "confidence_score": ev.confidence_score
                    }
                    for ev in practice.evidence
                ],
                "related_patterns": practice.related_patterns,
                "severity": practice.severity,
                "effort_to_fix": practice.effort_to_fix
            }
        }
        
        return self.submit_contribution(
            contributor_id=contributor_id,
            contribution_type=ContributionType.PRACTICE,
            title=f"Practice: {practice.name}",
            description=practice.description,
            content=content,
            tags=practice.tags,
            category=practice.practice_type.value
        )
    
    def submit_review(
        self,
        reviewer_id: str,
        contribution_id: str,
        status: ReviewStatus,
        rating: int,
        comments: str,
        suggestions: Optional[List[str]] = None
    ) -> ContributionReview:
        """Submit a review for a contribution"""
        
        if reviewer_id not in self.users:
            raise ValueError("Reviewer not found")
        
        if contribution_id not in self.contributions:
            raise ValueError("Contribution not found")
        
        # Check if user already reviewed this contribution
        existing_review = self._find_user_review(reviewer_id, contribution_id)
        if existing_review:
            # Update existing review
            existing_review.status = status
            existing_review.rating = rating
            existing_review.comments = comments
            existing_review.suggestions = suggestions or []
            existing_review.updated_at = datetime.now()
            return existing_review
        
        review_id = self._generate_id(f"review_{contribution_id}_{reviewer_id}")
        
        review = ContributionReview(
            id=review_id,
            contribution_id=contribution_id,
            reviewer_id=reviewer_id,
            status=status,
            rating=rating,
            comments=comments,
            suggestions=suggestions or []
        )
        
        self.reviews[review_id] = review
        self.contributions[contribution_id].reviews.append(review)
        
        # Update user stats
        self.users[reviewer_id].reviews_count += 1
        
        # Update contribution status based on reviews
        self._update_contribution_status(contribution_id)
        
        return review
    
    def create_discussion(
        self,
        author_id: str,
        title: str,
        content: str,
        related_pattern_ids: Optional[List[str]] = None,
        related_practice_ids: Optional[List[str]] = None,
        tags: Optional[Set[str]] = None
    ) -> KnowledgeDiscussion:
        """Create a new knowledge discussion"""
        
        if author_id not in self.users:
            raise ValueError("Author not found")
        
        discussion_id = self._generate_id(f"discussion_{title}_{author_id}")
        
        discussion = KnowledgeDiscussion(
            id=discussion_id,
            title=title,
            content=content,
            author_id=author_id,
            related_pattern_ids=related_pattern_ids or [],
            related_practice_ids=related_practice_ids or [],
            tags=tags or set()
        )
        
        self.discussions[discussion_id] = discussion
        return discussion
    
    def add_discussion_reply(
        self,
        discussion_id: str,
        author_id: str,
        content: str,
        parent_reply_id: Optional[str] = None
    ) -> DiscussionReply:
        """Add a reply to a discussion"""
        
        if discussion_id not in self.discussions:
            raise ValueError("Discussion not found")
        
        if author_id not in self.users:
            raise ValueError("Author not found")
        
        reply_id = self._generate_id(f"reply_{discussion_id}_{author_id}")
        
        reply = DiscussionReply(
            id=reply_id,
            discussion_id=discussion_id,
            author_id=author_id,
            content=content,
            parent_reply_id=parent_reply_id
        )
        
        self.discussions[discussion_id].replies.append(reply)
        return reply
    
    def vote_contribution(
        self,
        user_id: str,
        contribution_id: str,
        is_upvote: bool
    ) -> bool:
        """Vote on a contribution"""
        
        if user_id not in self.users or contribution_id not in self.contributions:
            return False
        
        contribution = self.contributions[contribution_id]
        
        if is_upvote:
            contribution.upvotes += 1
        else:
            contribution.downvotes += 1
        
        # Update contributor reputation
        contributor = self.users[contribution.contributor_id]
        reputation_change = 5 if is_upvote else -2
        contributor.reputation = max(0, contributor.reputation + reputation_change)
        
        return True
    
    def search_contributions(
        self,
        query: str = "",
        contribution_type: Optional[ContributionType] = None,
        status: Optional[ContributionStatus] = None,
        tags: Optional[Set[str]] = None,
        category: Optional[str] = None,
        contributor_id: Optional[str] = None
    ) -> List[CommunityContribution]:
        """Search community contributions"""
        
        results = set(self.contributions.keys())
        
        # Filter by type
        if contribution_type:
            results &= self.contributions_by_type.get(contribution_type, set())
        
        # Filter by status
        if status:
            results &= self.contributions_by_status.get(status, set())
        
        # Filter by contributor
        if contributor_id:
            results &= self.contributions_by_user.get(contributor_id, set())
        
        # Filter by tags
        if tags:
            tag_results = set()
            for tag in tags:
                tag_results |= self.contributions_by_tag.get(tag, set())
            results &= tag_results
        
        # Filter by category
        if category:
            category_results = {
                cid for cid, contrib in self.contributions.items()
                if contrib.category == category
            }
            results &= category_results
        
        # Text search
        if query:
            query_lower = query.lower()
            text_results = {
                cid for cid, contrib in self.contributions.items()
                if query_lower in contrib.title.lower() or
                   query_lower in contrib.description.lower()
            }
            results &= text_results
        
        contributions = [self.contributions[cid] for cid in results]
        
        # Sort by popularity (upvotes - downvotes) and recency
        contributions.sort(
            key=lambda c: (c.upvotes - c.downvotes, c.created_at),
            reverse=True
        )
        
        return contributions
    
    def get_trending_contributions(self, limit: int = 10) -> List[CommunityContribution]:
        """Get trending contributions based on recent activity"""
        
        # Simple trending algorithm: recent contributions with high vote ratio
        all_contributions = list(self.contributions.values())
        
        # Filter recent contributions (last 30 days)
        recent_cutoff = datetime.now().timestamp() - (30 * 24 * 60 * 60)
        recent_contributions = [
            c for c in all_contributions
            if c.created_at.timestamp() > recent_cutoff
        ]
        
        # Sort by engagement score
        def engagement_score(contrib):
            votes = contrib.upvotes + contrib.downvotes
            if votes == 0:
                return 0
            vote_ratio = contrib.upvotes / votes
            return vote_ratio * votes * (contrib.view_count + 1)
        
        recent_contributions.sort(key=engagement_score, reverse=True)
        return recent_contributions[:limit]
    
    def get_user_contributions(self, user_id: str) -> List[CommunityContribution]:
        """Get all contributions by a user"""
        contribution_ids = self.contributions_by_user.get(user_id, set())
        return [self.contributions[cid] for cid in contribution_ids]
    
    def get_user_reputation_breakdown(self, user_id: str) -> Dict[str, Any]:
        """Get detailed reputation breakdown for a user"""
        if user_id not in self.users:
            return {}
        
        user = self.users[user_id]
        contributions = self.get_user_contributions(user_id)
        
        return {
            "total_reputation": user.reputation,
            "contributions_count": user.contributions_count,
            "reviews_count": user.reviews_count,
            "upvotes_received": sum(c.upvotes for c in contributions),
            "downvotes_received": sum(c.downvotes for c in contributions),
            "expertise_areas": list(user.expertise_areas),
            "is_expert": user.is_expert,
            "is_moderator": user.is_moderator,
            "joined_at": user.joined_at.isoformat()
        }
    
    def promote_to_expert(self, user_id: str, expertise_areas: Set[str]) -> bool:
        """Promote a user to expert status"""
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        
        # Check criteria for expert promotion
        if (user.reputation >= 500 and
            user.contributions_count >= 5 and
            user.reviews_count >= 10):
            
            user.is_expert = True
            user.expertise_areas.update(expertise_areas)
            return True
        
        return False
    
    def get_community_statistics(self) -> Dict[str, Any]:
        """Get overall community statistics"""
        
        total_users = len(self.users)
        total_contributions = len(self.contributions)
        total_discussions = len(self.discussions)
        
        # Contributions by type
        contrib_by_type = {}
        for contrib_type in ContributionType:
            count = len(self.contributions_by_type.get(contrib_type, set()))
            contrib_by_type[contrib_type.value] = count
        
        # Contributions by status
        contrib_by_status = {}
        for status in ContributionStatus:
            count = len(self.contributions_by_status.get(status, set()))
            contrib_by_status[status.value] = count
        
        # Top contributors
        top_contributors = sorted(
            self.users.values(),
            key=lambda u: u.reputation,
            reverse=True
        )[:5]
        
        return {
            "total_users": total_users,
            "total_contributions": total_contributions,
            "total_discussions": total_discussions,
            "contributions_by_type": contrib_by_type,
            "contributions_by_status": contrib_by_status,
            "experts_count": len([u for u in self.users.values() if u.is_expert]),
            "moderators_count": len([u for u in self.users.values() if u.is_moderator]),
            "top_contributors": [
                {
                    "username": u.username,
                    "reputation": u.reputation,
                    "contributions": u.contributions_count
                }
                for u in top_contributors
            ]
        }
    
    def export_approved_patterns(self) -> List[ArchitecturalPattern]:
        """Export approved pattern contributions as ArchitecturalPattern objects"""
        
        approved_patterns = []
        
        for contribution in self.contributions.values():
            if (contribution.contribution_type == ContributionType.PATTERN and
                contribution.status == ContributionStatus.APPROVED):
                
                pattern_data = contribution.content.get("pattern_data", {})
                
                # Convert back to ArchitecturalPattern
                try:
                    pattern = ArchitecturalPattern(
                        id=f"community_{contribution.id}",
                        name=pattern_data["name"],
                        category=PatternCategory(pattern_data["category"]),
                        complexity=PatternComplexity(pattern_data["complexity"]),
                        description=pattern_data["description"],
                        intent=pattern_data["intent"],
                        structure=pattern_data["structure"],
                        participants=pattern_data["participants"],
                        collaborations=pattern_data["collaborations"],
                        consequences=pattern_data["consequences"],
                        implementation_notes=pattern_data["implementation_notes"],
                        examples=[],  # Would need to reconstruct PatternExample objects
                        common_violations=[],  # Would need to reconstruct PatternViolation objects
                        related_patterns=pattern_data["related_patterns"],
                        owl_axioms=pattern_data["owl_axioms"],
                        tags=contribution.tags,
                        created_at=contribution.created_at.isoformat(),
                        updated_at=contribution.updated_at.isoformat(),
                        author=self.users[contribution.contributor_id].username,
                        community_rating=contribution.upvotes / max(1, contribution.upvotes + contribution.downvotes),
                        usage_count=contribution.usage_count
                    )
                    
                    approved_patterns.append(pattern)
                    
                except (KeyError, ValueError) as e:
                    # Skip malformed patterns
                    continue
        
        return approved_patterns
    
    def export_approved_practices(self) -> List[BestPractice]:
        """Export approved practice contributions as BestPractice objects"""
        
        approved_practices = []
        
        for contribution in self.contributions.values():
            if (contribution.contribution_type == ContributionType.PRACTICE and
                contribution.status == ContributionStatus.APPROVED):
                
                practice_data = contribution.content.get("practice_data", {})
                
                # Convert back to BestPractice
                try:
                    practice = BestPractice(
                        id=f"community_{contribution.id}",
                        name=practice_data["name"],
                        practice_type=PracticeType(practice_data["practice_type"]),
                        context={PracticeContext(ctx) for ctx in practice_data["context"]},
                        description=practice_data["description"],
                        rationale=practice_data["rationale"],
                        when_to_apply=practice_data["when_to_apply"],
                        when_not_to_apply=practice_data["when_not_to_apply"],
                        implementation_steps=practice_data["implementation_steps"],
                        code_examples=practice_data["code_examples"],
                        detection_rules=practice_data["detection_rules"],
                        metrics=practice_data["metrics"],
                        evidence=[],  # Would need to reconstruct PracticeEvidence objects
                        related_patterns=practice_data["related_patterns"],
                        tags=contribution.tags,
                        severity=practice_data["severity"],
                        effort_to_fix=practice_data["effort_to_fix"],
                        created_at=contribution.created_at,
                        updated_at=contribution.updated_at,
                        author=self.users[contribution.contributor_id].username,
                        community_rating=contribution.upvotes / max(1, contribution.upvotes + contribution.downvotes),
                        usage_frequency=contribution.usage_count
                    )
                    
                    approved_practices.append(practice)
                    
                except (KeyError, ValueError) as e:
                    # Skip malformed practices
                    continue
        
        return approved_practices
    
    # Helper methods
    def _generate_id(self, seed: str) -> str:
        """Generate a unique ID from a seed string"""
        return hashlib.md5(f"{seed}_{datetime.now().isoformat()}".encode()).hexdigest()
    
    def _update_contribution_indices(self, contribution: CommunityContribution):
        """Update search indices for a contribution"""
        
        # Type index
        if contribution.contribution_type not in self.contributions_by_type:
            self.contributions_by_type[contribution.contribution_type] = set()
        self.contributions_by_type[contribution.contribution_type].add(contribution.id)
        
        # Status index
        if contribution.status not in self.contributions_by_status:
            self.contributions_by_status[contribution.status] = set()
        self.contributions_by_status[contribution.status].add(contribution.id)
        
        # Tag index
        for tag in contribution.tags:
            if tag not in self.contributions_by_tag:
                self.contributions_by_tag[tag] = set()
            self.contributions_by_tag[tag].add(contribution.id)
    
    def _find_user_review(self, user_id: str, contribution_id: str) -> Optional[ContributionReview]:
        """Find existing review by user for contribution"""
        contribution = self.contributions.get(contribution_id)
        if not contribution:
            return None
        
        for review in contribution.reviews:
            if review.reviewer_id == user_id:
                return review
        
        return None
    
    def _update_contribution_status(self, contribution_id: str):
        """Update contribution status based on reviews"""
        contribution = self.contributions[contribution_id]
        
        if not contribution.reviews:
            return
        
        # Simple approval logic: need at least 2 approved reviews from experts
        expert_approvals = 0
        expert_rejections = 0
        
        for review in contribution.reviews:
            reviewer = self.users[review.reviewer_id]
            if reviewer.is_expert:
                if review.status == ReviewStatus.APPROVED:
                    expert_approvals += 1
                elif review.status == ReviewStatus.REJECTED:
                    expert_rejections += 1
        
        if expert_approvals >= 2 and expert_rejections == 0:
            contribution.status = ContributionStatus.APPROVED
            contribution.approved_at = datetime.now()
            # Could set approved_by to the first expert reviewer
        elif expert_rejections >= 1:
            contribution.status = ContributionStatus.REJECTED
        else:
            contribution.status = ContributionStatus.UNDER_REVIEW