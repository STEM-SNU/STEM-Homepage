var source;
function dEI(elementID){
    return document.getElementById(elementID);
}

// GNB
function onTopNavi(viewNum, num){
    // if ( document.getElementById('gnb').getAttribute('class') &&document.getElementById('gnb').getAttribute('class') == 'start' ) {
    if ( jQuery('#gnb').hasClass('start') ) {

        for(var i = 1; i < num; i++){
            var onCategory = document.getElementById("item" + i);
            var onList = document.getElementById("m" + i);
            if(i === viewNum){
                onCategory.className = "on";
                if (onList) onList.style.visibility = "visible";
            } else {
                onCategory.className = "";
                if (onList) onList.style.visibility = "hidden";
            }
        }
    }
}

/* gnb load and 'header' mouse leave function - keep current menu selection */
function gnbLoadOpt() {
    jQuery('#gnb .on').removeClass('on').find('.on2').removeClass('on2');
    jQuery('#gnb>li[data-current]').addClass('on').find('[data-current]').addClass('on2');
    jQuery('#gnb>li>a>img').each( function() {
        if ( jQuery(this).parents('[data-current]').length==0 ) { jQuery(this).attr('src', jQuery(this).attr('src').replace('_on.gif','_off.gif') ); }
    });
    jQuery('#gnb>li[data-current]>a>img').each( function() {
        jQuery(this).attr('src', jQuery(this).attr('src').replace('_off.gif','_on.gif') );
    });
}
jQuery(document).ready( function() {
    jQuery('#gnb').addClass('start');
    jQuery('#gnb>li.on:first').attr('data-current','true');
    jQuery('#gnb>li.on').find('.on2:first').attr('data-current','true');
    gnbLoadOpt();
    jQuery('#header').mouseleave( function() {
        gnbLoadOpt();
    });
});