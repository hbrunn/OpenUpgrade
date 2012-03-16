openerp.web.page = function (openerp) {
    var _t = openerp.web._t,
       _lt = openerp.web._lt;

    openerp.web.views.add('page', 'openerp.web.PageView');
    openerp.web.PageView = openerp.web.FormView.extend({
        form_template: "PageView",
        display_name: _lt('Page'),
        init: function () {
            this._super.apply(this, arguments);
            this.registry = openerp.web.page.readonly;
            this.set({"force_readonly": true});
        },
        reload: function () {
            if (this.dataset.index == null) {
                this.do_prev_view();
                return $.Deferred().reject().promise();
            }
            return this._super();
        },
        on_loaded: function(data) {
            this._super(data);
            this.$form_header.find('button.oe_form_button_edit').click(this.on_button_edit);
            this.$form_header.find('button.oe_form_button_create').click(this.on_button_create);
            this.$form_header.find('button.oe_form_button_duplicate').click(this.on_button_duplicate);
            this.$form_header.find('button.oe_form_button_delete').click(this.on_button_delete);
        },
        on_button_edit: function() {
            return this.do_switch_view('form');
        },
        on_button_create: function() {
            this.dataset.index = null;
            return this.do_switch_view('form');
        },
        on_button_duplicate: function() {
            var self = this;
            var def = $.Deferred();
            $.when(this.has_been_loaded).then(function() {
                self.dataset.call('copy', [self.datarecord.id, {}, self.dataset.context]).then(function(new_id) {
                    return self.on_created({ result : new_id });
                }).then(function() {
                    return self.do_switch_view('form');
                }).then(function() {
                    def.resolve();
                });
            });
            return def.promise();
        },
        on_button_delete: function() {
            var self = this;
            var def = $.Deferred();
            $.when(this.has_been_loaded).then(function() {
                if (self.datarecord.id && confirm(_t("Do you really want to delete this record?"))) {
                    self.dataset.unlink([self.datarecord.id]).then(function() {
                        self.on_pager_action('next');
                        def.resolve();
                    });
                } else {
                    $.async_when().then(function () {
                        def.reject();
                    })
                }
            });
            return def.promise();
        }
    });

    /** @namespace */
    openerp.web.page = {};
    
    openerp.web.page.FieldSelectionReadonly = openerp.web.form.AbstractField.extend({
        form_template: 'FieldChar.readonly',
        init: function(view, node) {
            // lifted straight from r/w version
            var self = this;
            this._super(view, node);
            this.values = _.clone(this.field.selection);
            _.each(this.values, function(v, i) {
                if (v[0] === false && v[1] === '') {
                    self.values.splice(i, 1);
                }
            });
            this.values.unshift([false, '']);
        },
        set_value: function (value) {
            value = value === null ? false : value;
            value = value instanceof Array ? value[0] : value;
            var option = _(this.values)
                .detect(function (record) { return record[0] === value; });
            this._super(value);
            this.$element.find('div').text(option ? option[1] : this.values[0][1]);
        }
    });
    openerp.web.page.FieldReferenceReadonly = openerp.web.form.FieldMany2One.extend({
        set_value: function (value) {
            if (!value) {
                return this._super(null);
            }
            var reference = value.split(',');
            this.field.relation = reference[0];
            var id = parseInt(reference[1], 10);
            return this._super(id);
        },
        get_value: function () {
            if (!this.value) {
                return null;
            }
            var id;
            if (typeof this.value === 'number') {
                // name_get has not run yet
                id = this.value;
            } else {
                id = this.value[0];
            }
            return _.str.sprintf('%s,%d', this.field.relation, id);
        }
    });

    openerp.web.page.FieldBinaryImageReaonly = openerp.web.form.FieldBinaryImage.extend({
        update_dom: function() {
            this._super.apply(this, arguments);
            this.$element.find('.oe-binary').hide();
        }
    });
    openerp.web.page.FieldBinaryFileReadonly = openerp.web.form.FieldBinary.extend({
        form_template: 'FieldURI.readonly',
        start: function() {
            this._super.apply(this, arguments);
            var self = this;
            this.$element.find('a').click(function() {
                if (self.value) {
                    self.on_save_as();
                }
                return false;
            });
        },
        set_value: function(value) {
            this._super.apply(this, arguments);
            this.$element.find('a').show(!!value);
            if (value) {
                var show_value = _t("Download") + " " + (this.view.datarecord[this.node.attrs.filename] || '');
                this.$element.find('a').text(show_value);
            }
        }
    });
    openerp.web.page.readonly = openerp.web.form.widgets.extend({
        'selection' : 'openerp.web.page.FieldSelectionReadonly',
        'reference': 'openerp.web.page.FieldReferenceReadonly',
        'binary': 'openerp.web.page.FieldBinaryFileReadonly',
        'image': 'openerp.web.page.FieldBinaryImageReaonly'
    });
};
