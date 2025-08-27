import os
from dotenv import load_dotenv
from langchain_community.tools import TavilySearchResults

load_dotenv()

def get_search_tool():
    """Initialize and return the Tavily search tool."""
    try:
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEY not found in environment variables")
        
        search = TavilySearchResults(
            tavily_api_key=tavily_api_key,
            max_results=5
        )
        return search
    except Exception as e:
        raise Exception(f"Error initializing search tool: {str(e)}")

def search_related_resources(topic: str):
    """Search for educational resources related to a given topic."""
    try:
        search = get_search_tool()
        
        # Clean and extract the main subject from the topic
        # Remove common filler words and extract key concepts
        topic = topic.strip()
        
        # Extract main subject - use up to 100 chars but try to find natural breakpoints
        main_subject = topic[:100].strip()
        for breakpoint in ['.', '!', '?', ':', ';', '-']:
            first_part = main_subject.split(breakpoint)[0]
            if len(first_part) > 30:  # Ensure we have a meaningful chunk
                main_subject = first_part
                break
        
        # Construct targeted queries for different types of resources
        academic_query = f"{main_subject} academic papers research journals scholarly articles"
        educational_query = f"{main_subject} educational resources learning materials tutorials course"
        book_query = f"{main_subject} recommended books textbooks reading list"
        video_query = f"{main_subject} educational videos lectures explanations"
        
        # Perform searches with different queries to get diverse results
        results = []
        try:
            results.extend(search.invoke(academic_query))
        except Exception:
            pass
            
        try:
            results.extend(search.invoke(educational_query))
        except Exception:
            pass
            
        try:
            results.extend(search.invoke(book_query))
        except Exception:
            pass
            
        try:
            results.extend(search.invoke(video_query))
        except Exception:
            pass
        
        # If we have no results, try a more general search
        if not results:
            try:
                results = search.invoke(f"{main_subject} learning resources")
            except Exception:
                pass
        
        # Combine and deduplicate results
        seen_urls = set()
        resources = []
        
        # Score and rank results
        for result in results:
            url = result.get("url", "")
            title = result.get("title", "Untitled")
            content = result.get("content", "")
            
            # Skip if we've already seen this URL or if it's empty
            if url in seen_urls or not url:
                continue
                
            # Skip results that are likely not educational resources
            lower_title = title.lower()
            lower_content = content.lower()
            
            # Skip social media and video platforms unless they're educational
            skip_domains = ['facebook.com', 'twitter.com', 'instagram.com']
            if any(domain in url.lower() for domain in skip_domains):
                if not ('education' in lower_content or 'learn' in lower_content or 'course' in lower_content):
                    continue
            
            # Calculate relevance score based on educational terms in title and content
            edu_terms = ['learn', 'course', 'education', 'tutorial', 'guide', 'book', 'paper', 'research', 'study', 'academic']
            score = 0
            
            # Check title for educational terms
            for term in edu_terms:
                if term in lower_title:
                    score += 3  # Title matches are more important
                if term in lower_content:
                    score += 1
            
            # Add to resources with score
            seen_urls.add(url)
            resource = {
                "title": title,
                "url": url,
                "content": content,
                "score": score
            }
            resources.append(resource)
        
        # Sort by relevance score
        resources.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Remove score field before returning
        for resource in resources:
            if "score" in resource:
                del resource["score"]
        
        # Return the top 5 most relevant resources
        return resources[:5]
    except Exception as e:
        # Return empty list instead of raising exception to prevent workflow failure
        print(f"Error searching related resources: {str(e)}")
        return []