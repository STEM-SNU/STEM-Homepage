**STEM Homepage**
=====================

- Original design by forbiznet, modified by Taehee Jeong(5th), remodified by Sangjoon Lee(7th)

- Address: https://honor.snu.ac.kr/

**페이지 소개**
-----

1. [대외홍보용 페이지](#1)
  - About Us : 회장 인사말, 비전, 조직도, 오시는 길, 연락처
  - Activities : 학술, 대외교류, 봉사, 리더십, 활동연혁
  - People : 기수 별 프로필 (대외홍보용)
  - Join Us : 리쿠르팅 안내, 협력 단체, 후원 단체
  - Board : 공지, 뉴스, Q&A, 자유게시판
   
2. [어드민 페이지 (DB 관리 페이지)](#2)
  - User : 회원계정 관리
  - Board, Post, Comnt : 게시판, 게시글, 코멘트 관리
  - STEMemo : 메모 관리
  - History : STEM 활동연혁 관리
  - Banner : 배너 관리
  
3. [멤버 페이지 (STEMWare)](#3)
  - STEM Member Management System (SMMS) : STEM 회원 관리 시스템
  - STEM People : 기수 별 프로필 (내부교류용)
  - STEM Cloud : STEM 클라우드 서버 링크
  - Calendar : STEM 스케줄, Google 캘린더와 동기화
  - STEMemo : 메인 페이지에 공개되는 짧은 게시글 서비스
  - Board : 멤버 전용 게시판
  - Conference Record : 회의록 게시, 열람 서비스

**상세 안내**
-----

##### 1. 대외홍보용 페이지
회원가입 없이도 모두가 열람 가능한 페이지이다. 게시글 작성은 회원가입 시에만 가능하다.

  - About Us

    > 회장 인사말, 비전, 조직도, 오시는 길, 연락처의 5페이지로 구성
    > 전체 페이지가 정적 페이지로 설정되어 있으므로, html 코드 자체에서 컨텐츠 수정
    > 데스크톱 페이지와, 모바일 페이지 분리되어 있으므로, **양측 모두 수정**해야 함

  - Activities

    > 부서 별 활동소개, 활동연혁 등의 5페이지로 구성
    > 전체 페이지가 정적 페이지로 설정되어 있으므로, html 코드 자체에서 컨텐츠 수정
    > 데스크톱 페이지와, 모바일 페이지 분리되어 있으므로, **양측 모두 수정**해야 함
    > **활동연혁 수정은 어드민 페이지에서 가능**

  - People

    > 대외 공개용 프로필만 노출
    > 기수는 DB에서 자동으로 쿼리를 수행하므로 별도 수정이 필요 없음

  - Join Us

    > 리쿠르팅 안내, 협력 단체, 후원 단체의 3페이지로 구성
    > 전체 페이지가 정적 페이지로 설정되어 있으므로, html 코드 자체에서 컨텐츠 수정
    > 데스크톱 페이지와, 모바일 페이지 분리되어 있으므로, **양측 모두 수정**해야 함

  - Board

    > 공지, 뉴스, 자유게시판, Q&A의 3페이지로 구성
    > 상기 4개의 게시판에 맞추어 페이지 레이아웃이 맞추어졌기 때문에, **게시판의 수를 DB에서 4개가 아닌 다른 것으로 수정하면 안 됨**
    > **게시글 및 코멘트 수정은 어드민 페이지에서 가능**

----

##### 2. 어드민 페이지
어드민 계정(`*********`)만이 유일하게 접근 가능한 페이지이다. IT 담당자가 어드민 계정을 보유하며, 필요에 따라 임원진들과 공유한다.

  - User

    > 회원 계정 관리가능
    > **게시 이력이 있는 회원 계정 삭제 시 홈페이지가 깨질 가능성이 있으므로, 만약 계정 삭제 시에는 해당 계정의 게시글, 코멘트 등을 모두 지워야 한다.**
    > 위의 과정이 복잡하므로, 가능하면 삭제는 하지 말고 수정만 할 것.

  - Board, Post, Comnt

    > 대외용은 Public의 Suffix가 붙고, 내부용은 Member의 Suffix가 붙는다.
    > 대외용 Board는 홈페이지 레이아웃 문제 상 4개를 유지해야 한다.
    > 내부용 Board는 공지사항, 총동창회 게시판(Group 1 - Dashboard)은 필히 유지해야 한다.

  - STEMemo

    > STEMemo 게시글 관리 가능

  - History

    > 활동 연혁 관리 가능
    > 자세한 수정 방법은 하단 **사용법** 참조

  - Banner

    > 메인 페이지 배너 수정 가능
    > 자세한 수정 방법은 하단 **사용법** 참조

  - 기타 탭

    > Isactive, Department, File 등의 탭은 가능하면 건드리지 않으며, 긴급한 경우에 DB를 수정해야 하는 경우에만 건드린다.

----

##### 3. 멤버 페이지
공우 회원만 접근 가능한 페이지이다. 회장 혹은 총무의 경우 여기에서 이수 관리가 가능하고, 일반 회원은 이를 자유롭게 열람할 수 있다.

  - STEM Member Management System (SMMS) : STEM 회원 관리 시스템

    > 일반 회원은 이수현황/이수기준서/Active 회원신청(목록)의 3개 탭이 보임
    > 현 기수 총무 또는 회장은 출결 및 이수 관리/회원등록 관리의 2개 탭이 더 보임
    > 이수점수 관리 방법은 하단 **사용법** 참조

  - STEM People : 기수 별 프로필 (내부교류용)

    > 연락처 등 내부교류용 프로필 전체노출
    > 기수는 DB에서 자동으로 쿼리를 수행하므로 별도 수정이 필요 없음

  - STEM Cloud : STEM 클라우드 서버 링크

    > 클라우드 서버 링크
    > 모바일 환경에서는 클라우드용 어플리케이션 다운로드 페이지로 이동

  - Calendar : STEM 스케줄, Google 캘린더와 동기화

    > Google 캘린더와 동기화된 달력 제공
    > Google 캘린더(공우 계정)에서 일정 수정 시 실시간으로 반영

  - STEMemo : 메인 페이지에 공개되는 짧은 게시글 서비스

    > 메인 페이지 상에 최신 3개 글 항상 노출

  - Board : 멤버 전용 게시판

    > 공지사항 게시판, 총동창회 게시판, 부서 게시판, 친목 게시판 등
    > 회원마다 개인 게시판 제공
    > 게시판 주는 자신의 게시판 제목을 자유롭게 수정 가능
    > 필요에 따라 게시판 주를 이전할 수 있음

  - Conference Record : 회의록 게시, 열람 서비스

    > 회의록을 게시, 작성, 열람할 수 있는 서비스
    > 회의록 게시는 Active 회원만 가능

**사용법**
-----

##### 메인 페이지
  1. 회원 가입

    > 1. 홈페이지 메인 우측 로그인창의 회원가입을 클릭한다.
    > 2. 정보를 입력하고 가입한다.
    >  * 비밀번호는 SHA-512로 암호화된다.

  2. 스템 회원 가입

    > 1. IT부 팀장은 신입 기수 선발 직후 어드민 페이지를 통해 Dummy Account를 생성한다.
    > * ID : `*****`(인수인계받을것) , PW : `*****`(인수인계받을것) , E-mail : 신청서에 작성한 이메일, Name : 선발자 이름
    > * **Dummy Account의 Ismember 항목은 꼭 체크되어야 한다.**
    > 2. 신규 선발자에게 이메일로 가입 안내 메일을 보낸다.
    > 3. 신규 선발자는 자신의 이름, 이메일로 회원가입을 한다.
    > 4. Dummy Account의 계정정보를 통해 스템 회원임이 인증됨과 동시에 Dummy Account가 신규 선발자의 Account로 교체된다.
    > 5. 최초 로그인 시 정보 수정 알림이 뜨며, 정보를 입력한 후에는 알림이 뜨지 않는다.
    >  * 정보 수정 알림은 수정 후 90일이 지나면 다시 발생한다.
   
  3. 회원 정보 수정

    > 1. 로그인 후, 마이페이지로 들어간다.
    > * 최초 회원가입 또는 정보 수정 후 90일이 지난 경우 수정 알림이 뜨며 자동으로 이동된다.
    > 2. 정보를 수정한다. 스템 회원의 경우, 여러 정보를 입력할 수 있다.
    >  * **비밀번호 수정의 경우 비밀번호와 비밀번호 확인을 입력한다.**
    >  * **사진은 프로필 140x140px, 커버 사진은 423x200px 가 최적 사이즈이다.**
    > 3. 비밀번호 확인 란에 본인의 현재 비밀번호를 입력하고, **회원정보수정** 을 누른다.
      
  4. 게시판 사용

    > 1. 사용을 원하는 게시판에 들어가 글을 쓴다.
    > * 단, 공지와 뉴스 게시판은 어드민 계정(`*********`)만 작성 가능하다.
    > 2. 댓글을 달고 싶은 게시글에 들어가 댓글을 단다.
    > 3. 게시물은 삭제/수정이 가능하며, 댓글은 삭제가 가능하다.
   
-----

##### 어드민 페이지

  1. 일반 회원 → 스템 회원 등업
    
    > 1. 어드민 페이지에서 `Member` 탭으로 이동한다.
    > 2. 해당 회원 레코드를 찾아서 **`Edit record`** 를 누른다.
    > 3. **`Ismember`** 항목을 체크로 바꾼다.
    >  * **이미 스템 회원으로 등록되어있는 사용자를 선택하지 마세요**
    > 4. **`Submit`** 을 누른다.
    
  2. 스템 연혁 등록

    > 1. 어드민 페이지에서 `History` 탭으로 이동한다.
    > 2. **`Create`** 를 누른다.
    > 3. `Start`에 시작한 날짜, `End`에 끝난 날짜를 넣는다. 하루짜리면 `End`는 비워두고 `One-day Event` 에 체크한다.
    > 4. `Content` 에 설명을 입력한다.
    > 5. **`Submit`** 을 누른다.
  
  3. 배너 관리

    > 1. 웹 서버에서 홈페이지 디렉토리의 static/upload/mainbanner 폴더에 배너 이미지로 올리고자 하는 jpg 또는 png 파일을 업로드한다.
    > 2. `Banner` 탭에서 **`Create`**를 누르고, `src`에 업로드한 파일명 (`***.jpg`)을 넣는다.
    > * 배너에 링크를 넣고 싶은 경우 `href`에는 링크 주소를 넣는다.
    > * 이미지 로딩이 안되었을 때 설명문을 넣고 싶은 경우 `description`에는 설명을 넣는다.
    > 3. **`Submit`**을 누른다.

-----

##### 스템웨어

  1. 대시보드(메인 페이지)

    >**대시보드는 자신의 현재 업무 및 현재 스템에서 일어나고 있는 일들을 잘 볼 수 있게 구성된다.**

    >1. 이번 주 스템 일정(캘린더)
    >2. 최근 게시글 10개
    >3. 현재 활동 등급 및 이수 현황/내역(STEM 회원관리시스템)
    >4. STEMemo 작성 및 최신 3개 메모
    >5. 각종 게시판(공지, 총동창회, 개인, 즐겨찾기) 게시글 확인
  
  2. STEM 회원관리시스템에서 이수 관리하기

    > **회장, 부회장(총무)는 회원관리 시스템상에서 이수기준서 작성, 이수점수 관리 등이 가능하다.**

    >1. 이수 현황/내역에서 `관리자 옵션`의 검색 탭을 통해 모든 회원의 이수 현황을 검색 가능하다.

    >2. 이수기준서에서 해당 분기의 이수활동표 작성이 가능하며, 또한 신규 분기 개시 또한 가능하다.
    > * 신규 분기 개시는 **반드시 이전 분기의 결산 종료(우수회원 선발) 이후에 실행**하여야 한다.

    >3. 출결 및 이수관리에서 회원들의 활동점수 및 회의출결을 수정, 기록할 수 있다.
    > * 점수 및 출결은 버튼의 **클릭 즉시** DB에 반영된다.
    > * 이수표의 `변경사항 반영` 버튼을 클릭하면 반영된 결과로 다시 이수표를 업데이트해준다.

    >4. Active 회원 목록(신청)에서는 `관리자 옵션`의 활성화 버튼을 통해 Active 회원 모집을 할 수 있다.
    > * Active 회원 모집은 **회원등록 관리에서 Active 회원 초기화를 수행한 이후에 실행**하도록 한다.

    >5. 회원등록 관리에서는 Active 회원의 부서 이동, 혹은 회원들의 등급 조정이 가능하다.
    > * Active 회원의 일괄 초기화는 **반드시 해당 분기의 최종 회의(평가회의) 이후에 실행**하여야 한다.
    > * **회의 출결에서 출석, 결석자가 반영되지 않는 치명적인 오류가 생길 수 있으며, 이 경우 직접 출결 및 이수 관리 탭에서 회의 결석자를 반영해야 하는 불편함이 생긴다.**

    > 새 분기 Active 회원 모집 절차는 다음과 같이 정리될 수 있다.
    > 1. 이전 분기 평가회의 직후 Active 회원 초기화하기
    > 2. Active 회원 모집 활성화하고, 모집 공지 올리기
    > 3. 모집 기간이 끝나면 Active 회원 모집 비활성화하기
    > 4. 이수기준서 작성을 위한 새 분기 첫 임원회의 때 신규 분기 개시하고, 이수기준서 짜기

  3. 스템 캘린더

    > 1. 스템 일정 달력은 스템 구글 캘린더에서 가져온 데이터 및 스템 현재 업무들의 마감일을 보여준다.
    > 2. 스템 구글 캘린더에 일정을 추가하는 방법은 스템 내부 매뉴얼을 참조한다.
    > 3. 스템 업무들의 마감일을 달력에서 업무를 드래그하여 조정할 수 있으며, 클릭하면 해당 업무로 이동한다.

  4. STEMemo
    
    > 1. STEMemo는 공우 전체 회원이 알림글을 볼 수 있도록 간단히 게시를 가능케 하는 메모 서비스이다.
    > 2. 구인/구직 알림 등이 필요한 경우 STEMemo에 글을 게시하면 일정 기간 동안 대쉬보드에서 메모가 노출된다.

  5. STEM Cloud

    > 1. 클라우드 서버로 이동하는 단순 링크만 연결되어 있다.
    > 2. 자세한 사용법은 홈페이지의 STEM Cloud Documentation을 참조한다.

  6. 게시판
    
    > 멤버 게시판은 누구나 생성 가능하며, 생성 시에 자신이 게시판 주가 되어 게시판의 이름 수정 및 주인 이전이 가능하다.
    > 글을 쓸 때 파일을 추가할 수 있다. 
    > 즐겨찾고 싶은 게시판이 있는 경우, `즐겨찾기`를 클릭하면 대쉬보드의 게시판 모음에서 바로 그 게시판의 게시글들을 볼 수 있다.
    > * 기본적으로 잡담 게시판, 기수 게시판이 즐겨찾기로 설정되어 있다.

  7. 멤버 프로필 페이지
    
    > `스템 사람들` 에서 스템 회원을 누른 후 맨 아래의 `자세히 보기`를 누르면 회원의 프로필로 들어간다.
    > 다른 사람의 프로필에 댓글을 달거나, 태그를 달 수 있다.
    > 내 프로필의 경우 프로필을 수정할 수 있다.
    > 프로필 페이지에서 해당 회원의 개인 게시판으로 이동할 수 있다.

  8. 알림, 쪽지 시스템

    > 자신과 관련 있는 이벤트 또는 스템 전체 공지 등이 있을 때 알림 시스템을 통해 알림이 전달된다.
    > * 알림은 일정 기간이 지난 이후 자동으로 삭제된다.
    > 쪽지 서비스는 웹에서 멤버 간에 1:1로 이야기를 주고받아야 할 때 유용하게 사용 가능하며, 쪽지 내용을 수신자의 이메일로 알림으로 보낼 수 있다.
    > * 쪽지는 받은 쪽지와 보낸 쪽지가 쪽지함에 저장되는데, 직접 삭제 버튼을 눌러야 기록이 삭제된다.

  9. 회의록

    > **액티브 회원 전체는 각종 회의가 있을 때 회의록 시스템을 통해 회의 내역을 기록해야 한다.**

    > 1. 회의록 생성 탭에서 새로운 회의를 시작한다. 회의 구분, 장소, 날짜, 제목을 구체적으로 기재한다.
    > 2. 회의록 작성/수정 탭에서 회의록 작성을 시작한다. 임시저장 기능등을 적절히 활용하여 회의록이 저장되지 않고 삭제되는 불상사가 없도록 한다.
    > * 회의록의 수정은 ** 서기가 회의록을 최초 생성한 이후 1주일 동안 가능하다**. 이는 회의록의 신뢰도를 높이고, 조작을 방지하기 위한 조치이다.
    > 3. 전체 회원은 회의록 열람/검색 탭에서 모든 회의록을 열람해볼 수 있다. 검색 기능을 이용해 필요한 회의록만을 찾아볼 수 있다.