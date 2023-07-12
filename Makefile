BASEDIR=$(CURDIR)
DJANGO_PROJECT=$(BASEDIR)/wishiwashi

.DEFAULT: help
.PHONY: help
help:
	@echo '                                                                       '
	@echo 'Usage:                                                                 '
	@echo '   make serve                       serve site locally                 '
	@echo '   make servessl                    serve site locally over ssl        '
	@echo '   make test                        test site                          '
	@echo '   make jsx                         transform JSX -> native Javascript '
	@echo '                                                                       '


.PHONY: serve
serve:
	cd $(DJANGO_PROJECT) && django-admin.py runserver 0.0.0.0:8000

.PHONY: test
test:
	cd wishiwashi && \
		find . -type f -iname '*py,cover' -delete && \
		python manage.py collectstatic --noinput && \
		py.test --reuse-db -n2 --cov-report= --cov=. --cov-fail-under=70 

.PHONY: mincss
mincss:
	cd $(DJANGO_PROJECT) && python -mrcssmin < \
		external/styles/wishiwashi.css > \
		external/styles/wishiwashi.min.css

.PHONY: jsx
jsx:
	cd $(DJANGO_PROJECT)/external && /usr/local/bin/jsx --extension jsx jsx/ scripts/

.PHONY: servessl
servessl:
	cd $(DJANGO_PROJECT) && python manage.py runsslserver --addrport 0.0.0.0:8000 \
		--certificate /home/simon/WishiWashi/ssl/STAR_wishiwashi_com.pem \
		--key /home/simon/WishiWashi/ssl/STAR_wishiwashi_com.key
