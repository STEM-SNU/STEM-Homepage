<!-- #include virtual = common/dbcon.asp -->
<%
Dim PopStr
Dim Rs,Sql,MainColRec,NewColRec,PutColRec
Dim NoticeRec,FreeRec

CALL GET_PopInfo()
Set Rs=Server.CreateObject("ADODB.RecordSet")

'=============================공지,이벤트,고객게시판 Get============================'
Sql="Select Top 5 idx,title,regdate,boardidx From BBSList Where boardidx=1 AND ReLevel='A' Order By Idx DESC"
Rs.Open Sql,DBcon,1
IF Not(Rs.Bof Or Rs.Eof) Then BoardRec1=Rs.GetRows()
Rs.Close

Sql="Select Top 5 idx,title,regdate,boardidx From BBSList Where boardidx=2 AND ReLevel='A' Order By Idx DESC"
Rs.Open Sql,DBcon,1
IF Not(Rs.Bof Or Rs.Eof) Then BoardRec2=Rs.GetRows()
Rs.Close
'==================================================================================='

'================================= 전광판배너 Get ==================================='
Sql="SELECT Top 5 filenames,linkurl FROM mainbanneradmin WHERE bansort=1 Order BY listnum ASC, idx ASC"
Rs.Open Sql,DBcon,1
IF Not(Rs.Bof Or Rs.Eof) Then bannerRec1=Rs.GetRows
Rs.Close
'==================================================================================='

Set Rs=Nothing
DBcon.Close
Set DBcon=Nothing

Function PT_BoardTopList(Rec,actpage)
	Dim i,TitleImg
	IF IsArray(Rec) Then
		For i=0 To Ubound(Rec,2)
			NewIcon=""
			IF CDate(Rec(2,i))>Date() Then NewIcon="<img src='/images/ico_new.gif'  border='0' alt='NEW' align=absmiddle />"
			Response.Write "<dd><a href='"&actpage&"?mode=view&idx="&Rec(0,i)&"'>"&GetString(Rec(1,i),42)&" "&NewIcon&"</a><span>"&Replace(MID(Rec(2,i),3,8),"-",".")&"</span></dd>"
		Next
	Else
		Response.Write "<center style='text-align;center; font-size:11px; padding:35px 0;'>등록된 게시물이 없습니다.</center>"&Vbcrlf
	End IF
End Function

Function PT_MainthumbImage(Rec,w,h,index)
	IF IsArray(Rec) Then
		For i=0 To UBound(Rec,2)
			FirstYN=""

			IF i=0 Then FirstYN="_fist"

			IF Rec(1,i)="" Then
				Response.Write "<div class='t_panel_"&index&""&FirstYN&"'><div class='t_panel_"&index&"-wrapper'><img src='/upload/mainbanner/"&Rec(0,i)&"' width='"&w&"' height='"&h&"' border='0'></div></div>"&Vbcrlf
			Else
				Response.Write "<div class='t_panel_"&index&""&FirstYN&"'><div class='t_panel_"&index&"-wrapper'><a href="""&Rec(1,i)&"""><img src='/upload/mainbanner/"&Rec(0,i)&"' width='"&w&"' height='"&h&"' border='0'></a></div></div>"&Vbcrlf
			End IF
		Next
	End IF
End Function
%>

<!--#include virtual = "/inc/body.asp"-->
<!--#include virtual = "/inc/top.asp"-->
	<!--container-->
	<div id="container">
		<div class="m_con">
			<div class="m_visual">
				<script type="text/javascript" src="/js/jquery.cycle.all.min.js"></script>
				<div class="slideshow1">
					<%=PT_MainthumbImage(bannerRec1,730,450,1)%>
				</div>

				<style>
				.slideshow1{height:450px; overflow:hidden; width:730px; }
				.t_panel_1{display:none; height:450px; overflow:hidden; width:730px;}
				.t_panel_1_first{display:block; height:450px; overflow:hidden; width:730px;}
				.t_panel_1-wrapper{height:450px; margin:0; overflow:hidden; padding:0; position:relative; width:730px;}
				#slider_links1{clear:both; position:absolute; left:20px; top:440px; z-index:999;}
				#slider_links1 a{width:8px; height:8px; float:left; background-color: #D0D0D0; display:block; color: #D0D0D0; display:block; font-weight:bold; font-family:Arial, Helvetica, sans-serif; font-size:1px; line-height:1em; list-style:none; text-align:center; margin-right:3px;}			
				#slider_links1 a:hover{color: #970000; background: #970000; text-decoration:none;}
				#slider_links1 a.activeSlide {color: #970000; background: #970000;}
				</style>

				<SCRIPT LANGUAGE="JavaScript">
				<!--
				jQuery(function() {
					jQuery('.slideshow1').before('<div id="slider_links1">').cycle({
						fx: 'fade',
						speed: 500,	//이미지바뀌는속도
						timeout: 2500,
						//timeout makes things pause
						delay: 0, //처음시작시 딜레이시간
						pager: '#slider_links1',
						startingSlide: 0,
						pause: 1,
						pauseOnPagerHover:1
					});
				});
				//-->
				</SCRIPT>
			</div>
			<div class="m_contents">
				<!--#include virtual = "/inc/right_login.asp"-->
				<div class="m_recruit"><a href="javascript:go_menu('sub4_1')"><img src="/images/m_recruit.gif" /></a></div>
				<div><a href="javascript:go_menu('sub2_1')"><img src="/images/m_activities.gif" /></a></div>
			</div>
		</div>
		<div class="m_con2">
			<div class="m_notice_img"><img src="/images/m_notice_img.gif" /></div>
			<div class="m_notice">
				<dl>
					<dt><em><img src="/images/m_notice.gif" /></em><span><a href="javascript:go_menu('sub5_1')"><img src="/images/btn_more.gif" /></a></span></dt>
					<%=PT_BoardTopList(BoardRec1,"/sub/sub5_1.asp")%>
				</dl>
			</div>
			<div class="m_qna">
				<dl>
					<dt><em><img src="/images/m_qna.gif" /></em><span><a href="javascript:go_menu('sub5_2')"><img src="/images/btn_more.gif" /></a></span></dt>
					<%=PT_BoardTopList(BoardRec2,"/sub/sub5_2.asp")%>
				</dl>
			</div>
		</div>
	</div>
	<!--//container-->
<!--#include virtual = "/inc/footer.asp"-->
<%=PopStr%>