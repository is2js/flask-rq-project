### model을 고려하여, targets -> blogs + youtube로 패키지 나누기
1. targets 패키지를 `blogs`로 변경하고
2. youtube 패키지를 만들어, youtube.py를 만들고 init에 import한다
3. markdown_creator.py에서는 `from targets import *`를 blos, youtube 에서 import하도록 바꾼다.
    ```python
    # app/rss_sources/markdown_creator.py
    from blogs import *
    from youtube import *
    from urls import *
    
    
    class Markdown:
        #...
    ```