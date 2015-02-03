(function($) {

    var allPanels = $('.expandable > div').hide();

    $('.expandable > span > a').click(function() {
        $(this).parent().next().toggle();
        return false;
    });

})(jQuery);