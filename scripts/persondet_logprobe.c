#include <stdio.h>
#include <stdarg.h>
void imp_log_fun(int level,int option,int output,const char *tag,const char *file,int line,const char *func,const char *fmt,...) {
 if(level<5) return;
 va_list ap; va_start(ap,fmt);
 fprintf(stderr,"SDK[%s:%d %s] ",tag?tag:"",line,func?func:"");
 vfprintf(stderr,fmt,ap); va_end(ap);
}

__attribute__((constructor)) static void unbuffer(void) { setvbuf(stdout,0,_IONBF,0); }
