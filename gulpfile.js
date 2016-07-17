var gulp = require('gulp'),
    uglify = require('gulp-uglify'),
    rename = require('gulp-rename'),
    minifyCSS = require('gulp-minify-css'),
    browserSync = require('browser-sync').create(),
    gae = require('gulp-gae');

gulp.task('gae-serve', function () {
      gulp.src('app.yaml')
        .pipe(gae('dev_appserver.py', [], {
	          port: 8081,
	          host: '127.0.0.1',
	          admin_port: 8001,
	          admin_host: '127.0.0.1'
	        }));
});

gulp.task('gae-deploy', function () {
      gulp.src('app.yaml')
        .pipe(gae('appcfg.py', ['update'], {
	          version: 'dev',
	          oauth2: undefined // for value-less parameters 
	        }));
});

// Minify stlye.css
gulp.task('styles', function(){
    gulp.src('framework/css/style.css')
        .pipe(minifyCSS())
        .pipe(rename(function (path) {
            path.basename += ".min";
        }))
        .pipe(gulp.dest('framework/css/'));
});


gulp.task('default', ['gae-serve']);
