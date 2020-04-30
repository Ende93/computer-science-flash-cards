$(document).ready(function(){
    $('.js-delete').click(function (e) {
        e.preventDefault();
        const bool = window.confirm('Confirm delete this note?')
        if (bool) {
            location.href = this.href;
        }
    })
    if ($('.memorizePanel').length != 0) {

        $('.flipCard').click(function(){
            if ($('.cardFront').is(":visible") == true) {
                $('.cardFront').hide();
                $('.cardBack').show();
            } else {
                $('.cardFront').show();
                $('.cardBack').hide();
            }
        });
    }

    if ($('.cardForm').length != 0) {

        $('.cardForm').submit(function(){

            var frontTrim = $.trim($('#front').val());
            $('#front').val(frontTrim);
            var backTrim = $.trim($('#back').val());
            $('#back').val(backTrim);

            if (! $('#front').val() || ! $('#back').val()) {
                return false;
            }
        });
    }

    // to remove the short delay on click on touch devices
    FastClick.attach(document.body);
});
