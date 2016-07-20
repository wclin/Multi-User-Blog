$(document).ready(function () {
    $("input#newCommentSubmit").click(function(){
        var $form = $("#newCommentForm"),
            content = $form.find( "textarea[name='content']" ).val(),
            url = $form.attr( "action" );
        $.post( url, {content: content} )
            .success(function( data ) {
            window.location.replace(data.redirect);
            });
        $("#newCommentModal").modal('hide'); //hide popup
    });
    $("input#editCommentSubmit").click(function(){
        var $form = $("#editCommentForm"),
            content = $form.find( "textarea[name='content']" ).val(),
            url = $form.attr( "action" );
        $.post( url, {content: content} )
            .success(function( data ) {
            window.location.replace(data.redirect);
            });
        $("#editCommentModal").modal('hide'); //hide popup
    });
});