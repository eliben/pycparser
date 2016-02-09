#define a(x) x##_
#define b(x) _##x
#define c(x) _##x##_
#define d(x,y) _##x##y##_

void main(void) {
    int a(i);
    int b(j);
    int c(k);
    int d(q,s);
}
