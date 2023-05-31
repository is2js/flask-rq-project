1. 현재 `publisehd_parsed`는 `<class 'time.struct_time'>`타입으로서 tz정보를 무시하고 utc기준으로 만든다.
    - parsed되면 tz정보가 없어서 `utc로 제시하지 않는 rss` ex> 민족의학신문 등은 utc로 취급되어 kst + 9시간이 되어버린다.
    - **그래서 `다양한 형태`지만, `tz정보를 담고 있는 string`필드인 published를 이용해야한다**

2. 현재까지 받는 publisehd의 datetime string type종류
    - `Thu, 16 Feb 2023 06:09:06 GMT` : utc로 해석한다.
    - `Fri, 28 Apr 2023 00:00:00 +0000` : +0 된 것은 utc tz이다
    - `Wed, 27 Feb 2019 16:47:15 +0900` : +9 된 것으로 표시된 상태이며 kst tz이다.
    - `2023-05-31 07:36:19` : 민족의학신문 껏으로 `tz정보가 빠진 kst`이다.
    - `2023-05-15T07:30:29+00:00` : tzinfo가 있는 Y-m-D도 있다. T로 감별한다면 Thu, 와 중복될 수 있다

3. **전략: `GME`나 내부에 `+`를 포함하는 것은 tzinfo를 가진 utc형식이고, utc로 바로 변환한다**
    - 이 때, 다양한 format은 `python-dateutil`의 parse클래스객체를 만들어 parse하여 `tz정보를 가진 naive dt`를 만든다.
        - 이미 utc tzinfo가 들어가잇으므로 **`같은 utc`로 localize하면 에러나니 `astimezone`으로 처리해야한다** 
    - **그렇지 않은 형식은 tz없기 때문에 애초에 `kst`로 localize를 통해 kst정보로 만든다.**
    ```python
    def str_time_to_utc_and_kst(published):
        if not published:
            return None
    
        kst_tz = pytz.timezone("Asia/Seoul")
        date_parser = parser()
        if published.endswith("GMT") or "+" in published:
            utc_dt = date_parser.parse(published)
            utc_dt = utc_dt.astimezone(pytz.UTC)
            kst_dt = utc_dt.astimezone(kst_tz)
    
    
        else:
            kst_dt = kst_tz.localize(date_parser.parse(published))
            utc_dt = kst_dt.astimezone(pytz.UTC)
    
        return utc_dt, kst_dt
    ```