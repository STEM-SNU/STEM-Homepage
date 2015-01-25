<%
Page=GetPage()
PageSize=20
serboardsort=checkParameter("int",Request("serboardsort"))
Search=checkParameter("char",Request("Search"))
SearchStr=checkParameter("char",Request("SearchStr"))

IF search<>"title" AND search<>"writer" AND search<>"content" Then search="title"
IF BBsCode="" Or BBsCode=false Then BBsCode=1
IF serboardsort<>"" Then StrWhere = " AND boardsort=? "
IF storeidx<>"" Then StrWhere = " AND storeidx=? "
IF Searchstr<>"" Then StrWhere = StrWhere & " And "&Search&" LIKE N'%'+?+'%' "

Call HK_BBSSetup(BBsCode)
BBsViewModeChk("list")
'BBsSelectField=GetBoardSortSh(BBsCode,serboardsort)
TopSortListTag = GetBoardSortList(BBsCode,serBoardSort)

Sql="select top "&PageSize&" bbsList.idx,title,regdate,writer,relevel,DelYN,TopYn,readnum,publicYN,pwd,sortName,(select Count(*) From CommentAdmin Where boardidx=bbsList.idx) AS CommentCnt,imgnames from bbsList Left Outer Join BoardSort ON boardsort=boardsort.idx WHERE bbsList.boardidx=?"&StrWhere&" And bbsList.idx NOT IN (select top "&(Page-1)*PageSize&" idx from bbsList where boardidx=?"&StrWhere&" order by Topyn DESC,Ref desc, ReLevel ASC, Idx DESC) order by Topyn DESC,Ref desc, ReLevel ASC, bbsList.Idx DESC; select count(idx) from bbslist where boardidx=?"&StrWhere
Set objCmd = Server.CreateObject("ADODB.Command")
With objCmd
	.ActiveConnection = DBcon
	.CommandType = adCmdText
	.CommandText = Sql
	
	.Parameters.Append .CreateParameter("@Par", adBigint, adParamInput, 8, BBsCode)
	IF serboardsort<>"" Then .Parameters.Append .CreateParameter("@Par", adBigint, adParamInput, 8, serboardsort)
	IF storeidx<>"" Then .Parameters.Append .CreateParameter("@Par", adBigint, adParamInput, 8, storeidx)
	IF Searchstr<>"" Then .Parameters.Append .CreateParameter("@Par", adVarWchar, adParamInput, 100, Searchstr)
	.Parameters.Append .CreateParameter("@Par", adBigint, adParamInput, 8, BBsCode)
	IF serboardsort<>"" Then .Parameters.Append .CreateParameter("@Par", adBigint, adParamInput, 8, serboardsort)
	IF storeidx<>"" Then .Parameters.Append .CreateParameter("@Par", adBigint, adParamInput, 8, storeidx)
	IF Searchstr<>"" Then .Parameters.Append .CreateParameter("@Par", adVarWchar, adParamInput, 100, Searchstr)
	.Parameters.Append .CreateParameter("@Par", adBigint, adParamInput, 8, BBsCode)
	IF serboardsort<>"" Then .Parameters.Append .CreateParameter("@Par", adBigint, adParamInput, 8, serboardsort)
	IF storeidx<>"" Then .Parameters.Append .CreateParameter("@Par", adBigint, adParamInput, 8, storeidx)
	IF Searchstr<>"" Then .Parameters.Append .CreateParameter("@Par", adVarWchar, adParamInput, 100, Searchstr)
End With
Set Rs = objCmd.Execute()
Set objCmd = Nothing

IF Not(Rs.Bof Or Rs.Eof) Then
	Allrec=Rs.GetRows
	Record_Cnt=Rs.NextRecordSet
	TotalPage=Int((CInt(Record_Cnt(0))-1)/CInt(PageSize)) +1
	Count=Record_Cnt(0)
Else
	Count=0
	TotalPage=1
End IF

Function PT_BoardList
	Dim i,Num,LevelView,Depth,j,TitleView,TopTag,PublicIcon,NewIcon
	Num=GetTextNumDesc(Page,Pagesize,Count)
	IF IsArray(Allrec) Then
		For i=0 To UBound(Allrec,2)
			LevelView="" : TopTag=Num : PublicIcon="" : CommentCnt="" : NewIcon="" : TrBg="" : ImgTag="" : LevelICon=""
			IF Allrec(11,i)<>0 Then CommentCnt=" <span style='font-size:11px; font-weight:bold; color: #6FA2FF;'>["&Allrec(11,i)&"]</span>"

			IF Len(Allrec(4,i))<>1 Then
				LevelICon="<img src='/images/ico_reply.gif' align='absmiddle'>"
				LevelView="padding-left:"&(Len(Allrec(4,i))-1)*10&"px"
			End IF
			IF Allrec(6,i)="True" Then
				TopTag="Notice"
				TrBg="style='background: #F6F6F6;'"
			End IF
			IF Allrec(8,i)="True" AND Len(Allrec(4,i))=1 Then PublicIcon="<img src='/common/memberimg/public.gif' align='absmiddle'>"

			IF Allrec(5,i)="True" Then
				TitleView="삭제된 게시물입니다."
			Else
				IF Allrec(8,i)="True" AND Not(Allrec(9,i)="" Or IsNull(Allrec(9,i))) Then
					TitleView="<a href='#jLink' onclick=""goPwdpage('view',"&Allrec(0,i)&")"">"&Allrec(1,i)&"</a>"
				Else
					TitleView="<a href='?mode=view&storeidx="&storeidx&"&serboardsort="&serboardsort&"&page="&Page&"&idx="&Allrec(0,i)&"&search="&Search&"&searchstr="&SearchStr&"'>"&Allrec(1,i)&"</a>"
				End IF
			End IF

			IF CDate(Allrec(2,i))>DateAdd("d",-2,Date()) Then NewIcon="&nbsp;<img src='/images/ico_new.gif' align='absmiddle' border='0'>"

			IF Allrec(12,i)<>"" Then
				ImgTag="<div style='margin:0 5px 0 0;float:left;border:1px solid #E4E4E4; overflow: hidden;'><a href='?mode=view&page="&Page&"&idx="&Allrec(0,i)&"&search="&Search&"&searchstr="&SearchStr&"'><img src='/upload/board/"&getImageThumbFilename(Allrec(12,i))&"' border='0' "&ImgPerSize("board",70,50,getImageThumbFilename(Allrec(12,i)))&"></a></div>"
			End IF

			Response.Write "<tr "&TrBg&">"&Vbcrlf
			Response.Write "	<td class='num' align='center'>"&TopTag&"</td>"&Vbcrlf
			Response.Write "	<td class='title' style='text-align:left;padding:5px 0 5px 0; "&LevelView&";'><div>"&PublicIcon&" "&LevelICon & TitleView&CommentCnt& NewIcon &"</div></td>"&Vbcrlf
			Response.Write "	<td class='name' align='center'>"&Allrec(3,i)&"</td>"&Vbcrlf
			Response.Write "	<td class='date' align='center'>"&Left(Allrec(2,i),10)&"</td>"&Vbcrlf
			Response.Write "	<td class='hit' align='center'>"&Allrec(7,i)&"</td>"&Vbcrlf
			Response.Write "</tr>"&Vbcrlf

			Num=Num-1
		Next
	Else
		Response.Write "<tr><td colspan='5' align='center' height='150' style='vertical-align: middle;'>검색된 게시물이 없습니다.</td></tr>"&Vbcrlf
	End IF
End Function
%>