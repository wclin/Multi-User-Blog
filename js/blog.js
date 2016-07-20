$(document).ready(function () {
    $("input#commentSubmit").click(function(){
        var $form = $("#commentForm"),
            content = $form.find( "textarea[name='content']" ).val(),
            url = $form.attr( "action" );
        $.post( url, {content: content} )
            .success(function( data ) {
            window.location.replace(data.redirect);
            });
        $("#commentModal").modal('hide'); //hide popup
    });
});