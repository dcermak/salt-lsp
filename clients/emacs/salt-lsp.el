;;; salt-lsp.el --- Salt LSP support

;;; Commentary:

;; Emacs package to integrate salt_lsp into lsp-mode

;;; Code:

(require 'lsp-mode)
(require 'salt-mode)

(add-to-list 'lsp-language-id-configuration '(salt-mode . "salt"))

(lsp-register-client
 (make-lsp-client
  :new-connection (lsp-stdio-connection (lambda ()'("python3" "-m" "salt_lsp")))
  :activation-fn (lsp-activate-on "salt")
  :server-id 'salt-lsp))

(provide 'salt-lsp)
;;; salt-lsp.el ends here
