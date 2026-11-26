void test_enter(void);
void test_exit(void);
#define taskENTER_CRITICAL() test_enter()
#define taskEXIT_CRITICAL() test_exit()
