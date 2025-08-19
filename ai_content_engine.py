#!/usr/bin/env python3
"""
AI Content Creation Engine for Kaushal Bot
Using Google Gemini AI - Following the Orchestrator-Workers pattern from GuideForEffectiveAgent.txt
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.schema import HumanMessage, SystemMessage

from config import GOOGLE_API_KEY
from database import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ContentRequest:
    """Content generation request"""
    user_id: int
    content_type: str  # 'post', 'comment', 'article', 'carousel'
    topic: str
    industry: str
    tone: str  # 'professional', 'casual', 'enthusiastic', 'thoughtful'
    length: str  # 'short', 'medium', 'long'
    hashtags: bool = True
    emoji: bool = True
    call_to_action: bool = True

@dataclass
class ContentResponse:
    """AI-generated content response"""
    content: str
    hashtags: List[str]
    suggested_time: str
    engagement_tips: List[str]
    linkedin_tips: List[str]

class ContentOrchestrator:
    """Main orchestrator for content creation workflow"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.7,
            google_api_key=GOOGLE_API_KEY,
            convert_system_message_to_human=True
        )
        self.content_worker = ContentWorker(self.llm)
        self.optimization_worker = OptimizationWorker(self.llm)
        self.analytics_worker = AnalyticsWorker(self.llm)
        self.refinement_worker = RefinementWorker(self.llm)
    
    async def create_content(self, request: ContentRequest) -> ContentResponse:
        """Main orchestration method for content creation"""
        logger.info(f"Starting content creation for user {request.user_id}")
        
        try:
            # Step 1: Generate base content
            base_content = await self.content_worker.generate_content(request)
            
            # Step 2: Optimize for LinkedIn
            optimized_content = await self.optimization_worker.optimize_for_linkedin(
                base_content, request
            )
            
            # Step 3: Generate engagement tips
            engagement_tips = await self.analytics_worker.generate_engagement_tips(
                optimized_content, request
            )
            
            # Step 4: Save to database
            await self._save_content_to_db(request, optimized_content)
            
            return ContentResponse(
                content=optimized_content['content'],
                hashtags=optimized_content['hashtags'],
                suggested_time=optimized_content['suggested_time'],
                engagement_tips=engagement_tips,
                linkedin_tips=optimized_content['linkedin_tips']
            )
            
        except Exception as e:
            logger.error(f"Content creation failed: {e}")
            raise
    
    async def refine_content(self, previous_content: str, instruction: str, industry: str, tone: str, length: str) -> Dict:
        """Refine an existing content draft based on user instructions"""
        logger.info("Refining content based on user instruction")
        refined = await self.refinement_worker.refine(previous_content, instruction, industry, tone, length)
        return refined

    async def _save_content_to_db(self, request: ContentRequest, content: Dict):
        """Save generated content to database"""
        post_data = {
            'user_id': request.user_id,
            'content': content['content'],
            'post_type': request.content_type,
            'status': 'draft',
            'ai_generated': True,
            'topic': request.topic,
            'industry': request.industry,
            'tone': request.tone,
            'hashtags': content['hashtags'],
            'engagement_tips': content.get('engagement_tips', []),
            'linkedin_tips': content.get('linkedin_tips', []),
            'suggested_time': content.get('suggested_time', ''),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        db.save_post(**post_data)

class ContentWorker:
    """Worker for generating base content"""
    
    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm
        self.content_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert LinkedIn content creator specializing in {industry}.
            
Your task is to create engaging, professional LinkedIn content that:
- Provides genuine value to the audience
- Uses storytelling and personal insights
- Includes relevant industry insights
- Maintains a {tone} tone
- Is optimized for LinkedIn's algorithm

Content Guidelines:
- Start with a compelling hook
- Use bullet points and short paragraphs
- Include personal experiences when relevant
- End with a thought-provoking question or call-to-action
- Keep it authentic and professional

Length Guidelines:
- Short: 100-200 words
- Medium: 200-400 words  
- Long: 400-600 words

Generate content in JSON format with these fields:
- content: The main post text
- hashtags: 3-5 relevant hashtags
- suggested_time: Best time to post (e.g., "Tuesday 9 AM")
- linkedin_tips: 2-3 LinkedIn-specific optimization tips"""),
            ("human", """Create LinkedIn content about: {topic}

Industry: {industry}
Tone: {tone}
Length: {length}
Include hashtags: {hashtags}
Include emoji: {emoji}
Include call-to-action: {call_to_action}""")
        ])
    
    async def generate_content(self, request: ContentRequest) -> Dict:
        """Generate base content based on request"""
        logger.info(f"Generating content for topic: {request.topic}")
        
        # Format boolean values for prompt
        hashtags_str = "Yes" if request.hashtags else "No"
        emoji_str = "Yes" if request.emoji else "No"
        cta_str = "Yes" if request.call_to_action else "No"
        
        messages = self.content_prompt.format_messages(
            industry=request.industry,
            tone=request.tone,
            topic=request.topic,
            length=request.length,
            hashtags=hashtags_str,
            emoji=emoji_str,
            call_to_action=cta_str
        )
        
        response = await self.llm.ainvoke(messages)
        
        try:
            # Parse JSON response
            content_data = json.loads(response.content)
            return content_data
        except json.JSONDecodeError:
            # Fallback: treat as plain text
            return {
                'content': response.content,
                'hashtags': [],
                'suggested_time': 'Tuesday 9 AM',
                'linkedin_tips': ['Post during business hours', 'Engage with comments']
            }

class OptimizationWorker:
    """Worker for LinkedIn-specific optimization"""
    
    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm
        self.optimization_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a LinkedIn optimization expert. Your job is to enhance content for maximum engagement on LinkedIn.

Optimization Guidelines:
1. **Hook Optimization**: Ensure the first line is compelling
2. **Readability**: Use proper spacing, bullet points, and emojis
3. **Hashtag Strategy**: Use 3-5 relevant, trending hashtags
4. **Call-to-Action**: Include clear, actionable CTAs
5. **Length**: Optimize for LinkedIn's character limits
6. **Timing**: Suggest optimal posting times

Return the optimized content in JSON format with:
- content: Optimized post text
- hashtags: Optimized hashtag list
- suggested_time: Best posting time
- linkedin_tips: Specific LinkedIn optimization tips"""),
            ("human", """Optimize this LinkedIn content:

{content}

Original hashtags: {hashtags}
Industry: {industry}
Tone: {tone}""")
        ])
    
    async def optimize_for_linkedin(self, content: Dict, request: ContentRequest) -> Dict:
        """Optimize content specifically for LinkedIn"""
        logger.info("Optimizing content for LinkedIn")
        
        messages = self.optimization_prompt.format_messages(
            content=content.get('content', ''),
            hashtags=content.get('hashtags', []),
            industry=request.industry,
            tone=request.tone
        )
        
        response = await self.llm.ainvoke(messages)
        
        try:
            optimized_data = json.loads(response.content)
            return optimized_data
        except json.JSONDecodeError:
            # Return original content if parsing fails
            return content

class AnalyticsWorker:
    """Worker for engagement analytics and tips"""
    
    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm
        self.analytics_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a LinkedIn engagement expert. Analyze content and provide specific tips for maximizing engagement.

Provide 3-5 actionable engagement tips based on:
- Content type and topic
- Industry best practices
- LinkedIn algorithm preferences
- Audience engagement patterns

Focus on practical, implementable advice."""),
            ("human", """Analyze this LinkedIn content and provide engagement tips:

Content: {content}
Topic: {topic}
Industry: {industry}
Content Type: {content_type}""")
        ])
    
    async def generate_engagement_tips(self, content: Dict, request: ContentRequest) -> List[str]:
        """Generate engagement tips for the content"""
        logger.info("Generating engagement tips")
        
        messages = self.analytics_prompt.format_messages(
            content=content.get('content', ''),
            topic=request.topic,
            industry=request.industry,
            content_type=request.content_type
        )
        
        response = await self.llm.ainvoke(messages)
        
        # Parse tips from response
        tips_text = response.content
        tips = [tip.strip() for tip in tips_text.split('\n') if tip.strip()]
        
        return tips[:5]  # Return max 5 tips

class RefinementWorker:
    """Worker for rewriting content based on user instructions"""
    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm
        self.refine_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a professional LinkedIn editor. Rewrite the given LinkedIn post according to the user's instructions while keeping it engaging, concise, and optimized for LinkedIn. Preserve the core meaning, but adapt voice and structure as requested. Return JSON with fields: content, hashtags (3-5), suggested_time, linkedin_tips (2-3)."""),
            ("human", """Original Post:\n{original_content}\n\nInstructions:\n{instruction}\n\nConstraints:\n- Industry: {industry}\n- Tone: {tone}\n- Length: {length} (short~150 words, medium~300 words, long~500 words)\n- Keep authenticity; avoid exaggeration.\n- If not specified, infer reasonable hashtags.""")
        ])

    async def refine(self, original_content: str, instruction: str, industry: str, tone: str, length: str) -> Dict:
        messages = self.refine_prompt.format_messages(
            original_content=original_content,
            instruction=instruction,
            industry=industry,
            tone=tone,
            length=length
        )
        response = await self.llm.ainvoke(messages)
        try:
            data = json.loads(response.content)
            return data
        except json.JSONDecodeError:
            return {
                'content': response.content,
                'hashtags': [],
                'suggested_time': 'Tuesday 9 AM',
                'linkedin_tips': ['Ask a question at the end', 'Use a relevant visual']
            }

class ContentTemplates:
    """Pre-built content templates for common scenarios"""
    
    @staticmethod
    def get_industry_templates() -> Dict[str, str]:
        """Get industry-specific content templates"""
        return {
            'technology': "Tech innovation insights and industry trends",
            'marketing': "Digital marketing strategies and brand building",
            'finance': "Financial insights and investment strategies", 
            'healthcare': "Healthcare innovation and patient care",
            'education': "Learning strategies and educational insights",
            'consulting': "Business strategy and consulting insights",
            'startup': "Entrepreneurship and startup growth",
            'general': "Professional development and career insights"
        }
    
    @staticmethod
    def get_tone_templates() -> Dict[str, str]:
        """Get tone-specific content templates"""
        return {
            'professional': "Formal, authoritative, industry expert tone",
            'casual': "Friendly, approachable, conversational tone",
            'enthusiastic': "Energetic, passionate, motivational tone",
            'thoughtful': "Reflective, analytical, insightful tone"
        }

# Global orchestrator instance
content_orchestrator = ContentOrchestrator()

async def create_linkedin_content(
    user_id: int,
    topic: str,
    industry: str = "general",
    tone: str = "professional",
    content_type: str = "post",
    length: str = "medium",
    hashtags: bool = True,
    emoji: bool = True,
    call_to_action: bool = True
) -> ContentResponse:
    """Main function to create LinkedIn content"""
    
    request = ContentRequest(
        user_id=user_id,
        content_type=content_type,
        topic=topic,
        industry=industry,
        tone=tone,
        length=length,
        hashtags=hashtags,
        emoji=emoji,
        call_to_action=call_to_action
    )
    
    return await content_orchestrator.create_content(request)

async def refine_linkedin_content(
    previous_content: str,
    instruction: str,
    industry: str = "general",
    tone: str = "professional",
    length: str = "medium",
) -> ContentResponse:
    """Refine a LinkedIn post based on user instruction"""
    refined = await content_orchestrator.refine_content(previous_content, instruction, industry, tone, length)
    # Wrap to ContentResponse-like object for downstream compatibility
    return ContentResponse(
        content=refined.get('content', ''),
        hashtags=refined.get('hashtags', []),
        suggested_time=refined.get('suggested_time', ''),
        engagement_tips=[],
        linkedin_tips=refined.get('linkedin_tips', [])
    )

async def get_content_suggestions(user_id: int, industry: str = "general") -> List[str]:
    """Get content topic suggestions based on industry"""
    
    suggestions_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a content strategist for {industry} professionals. Provide 5 engaging LinkedIn post topics that would resonate with this audience."),
        ("human", "Generate 5 LinkedIn post topics for {industry} professionals. Return as a JSON array of strings.")
    ])
    
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7, google_api_key=GOOGLE_API_KEY, convert_system_message_to_human=True)
    
    messages = suggestions_prompt.format_messages(industry=industry)
    response = await llm.ainvoke(messages)
    
    try:
        suggestions = json.loads(response.content)
        return suggestions if isinstance(suggestions, list) else []
    except json.JSONDecodeError:
        # Fallback suggestions
        return [
            f"Key trends in {industry} for 2024",
            f"Lessons learned from my {industry} journey",
            f"Common mistakes in {industry} and how to avoid them",
            f"The future of {industry}",
            f"Building relationships in {industry}"
        ]
