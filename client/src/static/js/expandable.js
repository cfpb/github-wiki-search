(function($) {

    var allPanels = $('.expandable > dd').hide();

    $('.expandable > dt > a').click(function() {
        $(this).parent().next().toggle();
        return false;
    });

})(jQuery);