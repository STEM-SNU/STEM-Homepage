var stemApp = angular.module('stemApp',[]);

stemApp.config(['$interpolateProvider', function($interpolateProvider) {
  $interpolateProvider.startSymbol('{[');
  $interpolateProvider.endSymbol(']}');
}]);

var person = function(id, name, img) {
    this.id = id;
    this.name = name;
    this.picture = 'images/' + img;
    this.department = 'Department';
    this.description = 'Jon loves to longboard, ride fixie, and drive stick because, as he says, the journey is just as important as the destination.';
    this.social = 'https://facebook.com/FredJeong';
    this.cover = '';
}

var memberListScope;

stemApp.controller('memberList', function($scope, $timeout) {
    memberListScope = $scope;
    $scope.members = [];
    $scope.pIndex = 0;
    $scope.openCard = function(id) {openCard($scope, id);};
    $scope.diviSion = function(mem){
        return mem.stem_dept === '봉사부' || mem.stem_dept === '학술부' || mem.stem_dept === '대외교류부';
    };
    $scope.preSident = function(mem){
        return mem.stem_dept === '회장' || mem.stem_dept === '총무';
    };
    jQuery.ajax({
        url: "/people",
        type: "GET",
        success: function(data){
            $scope.members = data;
            $scope.all_members = [[data[0]]];
            var cnt = 0;
            for (var i=1; i < data.length; i++) {
                if (data[i-1].cycle !== data[i].cycle) {
                    cnt++;
                    $scope.all_members.push([data[i]]);
                } else $scope.all_members[cnt].push(data[i]);
            }
            $scope.$apply();
        }
    });
    $timeout(function(){
        (function($) {
            $(".member-picture-thumb").each(function(i, elem) {
                if (elem.naturalWidth < elem.naturalHeight)
                    $(this).addClass("portrait");
            });
        })(jQuery);}, 500);
    $scope.prevMember = function(){return prevMember($scope);};
    $scope.nextMember = function(){return nextMember($scope);};
    $scope.goNext = function(){goNext($scope);};
    $scope.goPrev = function(){goPrev($scope);};
});

function openCard($scope, id) {
    for (var i = 0; i < $scope.members.length; i++) {
        if($scope.members[i].id === id) {
            $scope.pIndex = i;
            jQuery(".member-card").trigger('openModal');
            return;
        }
    }
}

function goNext($scope) {
    $scope.pIndex++;
    $scope.pIndex %= $scope.members.length;
}

function goPrev($scope) {
    $scope.pIndex += $scope.members.length - 1;
    $scope.pIndex %= $scope.members.length;
}

function nextMember($scope) {
    return $scope.members[($scope.pIndex + 1) % $scope.members.length];
}

function prevMember($scope) {
    return $scope.members[($scope.pIndex + $scope.members.length - 1) % $scope.members.length];
}