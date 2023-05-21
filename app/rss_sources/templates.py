TITLE_TEMPLATE = '''\
{} {} <small>(최근 업데이트:{})</small>    
<!-- START -->
'''

TABLE_START = '''\
<div align="center">
    <table>
'''

TABLE_END = '''\
    </table>
</div>
<!-- END -->

'''

YOUTUBE_CUSTOM_TEMPLATE = '''
<div align="center">
    <a href="https://www.youtube.com/channel/{}?sub_confirmation=1"><img src="https://img.shields.io/badge/-구독하기-red?style=flat&logo=youtube&logoColor=white" height=25px/></a>
</div>
'''

YOUTUBE_FEED_TEMPLATE = '''\
        <tr>
            <td align="center" width="140px" style="background:black;" style="padding:0;">
                <a href="{}">
                    <img width="140px" src="{}" style="margin:0;">
                </a>
            </td>
            <td>
                <h5>
                    <a href="{}" style="color:red;text-decoration: none;">
                        {}
                    </a>
                </h5>
                <sup><sub>{}{}</sub></sup>
            </td>
        </tr>
'''


BLOG_FEED_TEMPLATE = '''\
        <tr>
            <td align="center" width="120px" style="padding:0;">
                <a href="{}">
                    <img width="120px" src="{}" style="margin:0;" alt="empty">
                </a>
            </td>
            <td>
                <h5>
                    <a href="{}" style="color:teal;text-decoration: none;">
                        {}
                    </a>
                </h5>
                <sup><sub>{}{}</sub></sup>
            </td>
        </tr>
'''

URL_FEED_TEMPLATE = '''\
        <tr>
            <td align="center" width="120px" style="padding:0;">
                <h6>
                    <a href="{}" style="color:grey;text-decoration: none;">
                        {}
                    </a>
                </h6>
                <sup><sub>{}</sub></sup>
            </td>
            <td>
                <h5>
                    <a href="{}" style="color:black;text-decoration: none;">
                        {}
                    </a>
                </h5>
                <sup><sub>{}</sub></sup>
            </td>
        </tr>
'''