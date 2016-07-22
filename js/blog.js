$(document).ready(function () {
    $("input#newPostSubmit").click(function(){
        var $form = $("#newPostForm"),
            title = $form.find("input[name='title']").val(),
            content = $form.find( "textarea[name='content']" ).val(),
            url = $form.attr( "action" );
        $.post( url, {title: title, content: content} )
            .always(function( data ) {
                if (data.redirect) {
                    window.location.replace(data.redirect);
                }
                else {
                    window.location.reload();
                }
            });
    });
    $("input#editPostSubmit").click(function(){
        var $form = $("#editPostForm"),
            title = $form.find("input[name='title']").val(),
            content = $form.find( "textarea[name='content']" ).val(),
            url = $form.attr( "action" );
        $.post( url, {title: title, content: content} )
            .always(function( data ) {
                if (data.redirect) {
                    window.location.replace(data.redirect);
                }
                else {
                    window.location.reload();
                }
            });
    });
    $("input#newCommentSubmit").click(function(){
        var $form = $("#newCommentForm"),
            content = $form.find( "textarea[name='content']" ).val(),
            url = $form.attr( "action" );
        $.post( url, {content: content} )
            .always(function( data ) {
                if (data.redirect) {
                    window.location.replace(data.redirect);
                }
                else {
                    window.location.reload();
                }
            });
    });
    $("input#editCommentSubmit").click(function(){
        var $form = $("#editCommentForm"),
            content = $form.find( "textarea[name='content']" ).val(),
            url = $form.attr( "action" );
        $.post( url, {content: content} )
            .always(function( data ) {
                if (data.redirect) {
                    window.location.replace(data.redirect);
                }
                else {
                    window.location.reload();
                }
            });
    });
});
$("#editCommentModal").addEventListener("load", function(event) {
    // Need fix
});

